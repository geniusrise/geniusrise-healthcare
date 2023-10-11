import base64
from typing import Any, Dict, List, Optional
import os
import logging

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

import cherrypy
from geniusrise import BatchInput, BatchOutput, Bolt, State
from transformers import AutoModel, AutoTokenizer

from geniusrise_healthcare.base import (
    ner,
    semantic_search_snomed,
    generate_follow_up_questions_from_concepts,
    generate_snomed_graph_from_concepts,
    generate_summary_from_qa,
)
from geniusrise_healthcare.io import load_concept_dict, load_faiss_index, load_networkx_graph
from geniusrise_healthcare.model import load_huggingface_model


log = logging.getLogger(__file__)


class InPatientAPI(Bolt):
    def __init__(
        self,
        input: BatchInput,
        output: BatchOutput,
        state: State,
        **kwargs,
    ) -> None:
        super().__init__(input=input, output=output, state=state)
        log.info("Loading in-patient API server")

    def load_models(
        self,
        llm_model: str = "/run/media/ixaxaar/models_f/models/Mistral-7B-v0.1",
        ner_model: str = "emilyalsentzer/Bio_ClinicalBERT",
        networkx_graph: str = "./saved/snomed.graph",
        faiss_index: str = "./saved/faiss.index",
        concept_id_to_concept: str = "./saved/concept_id_to_concept.pickle",
        description_id_to_concept: str = "./saved/description_id_to_concept.pickle",
    ) -> None:
        """Load all required models and tokenizers."""

        log.warn(f"Loading model {llm_model}")
        self.model, self.tokenizer = load_huggingface_model(
            llm_model,
            use_cuda=True,
            precision="float16",
            quantize=False,
            quantize_bits=8,
            use_safetensors=True,
            trust_remote_code=True,
        )
        log.warn(f"Loading graph {networkx_graph}")
        self.G = load_networkx_graph(networkx_graph)
        log.warn(f"Loading FAISS index {faiss_index}")
        self.faiss_index = load_faiss_index(faiss_index, use_cuda=False)
        log.warn(f"Loading lookup dictionaries {concept_id_to_concept} {description_id_to_concept}")
        self.concept_id_to_concept = load_concept_dict(concept_id_to_concept)
        self.description_id_to_concept = load_concept_dict(description_id_to_concept)

        if ner_model != "emilyalsentzer/Bio_ClinicalBERT":
            log.warn(f"Loading NER model {ner_model}")
            self.ner_model, self.ner_tokenizer = load_huggingface_model(
                ner_model, use_cuda=True, device_map=None, precision="float32", model_class_name="AutoModel"
            )
        else:
            self.ner_tokenizer = AutoTokenizer.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
            self.ner_model = AutoModel.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")

    def _check_auth(self, username: str, password: str) -> None:
        """Check if the provided username and password are correct."""
        auth_header = cherrypy.request.headers.get("Authorization")
        if auth_header:
            auth_decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            provided_username, provided_password = auth_decoded.split(":", 1)
            if provided_username != username or provided_password != password:
                raise cherrypy.HTTPError(401, "Unauthorized")
        else:
            raise cherrypy.HTTPError(401, "Unauthorized")

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    @cherrypy.tools.allow(methods=["POST"])
    def ner(self, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        if username and password:
            self._check_auth(username=username, password=password)
        data = cherrypy.request.json
        user_input = data.get("user_input", "")
        symptoms_diseases = data.get("symptoms_diseases", [])
        type_ids_filter = data.get("type_ids_filter", [])
        return ner(
            user_input=user_input,
            model=self.model,
            tokenizer=self.tokenizer,
            type_ids_filter=type_ids_filter,
            symptoms_and_diseases=symptoms_diseases,
        )

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    @cherrypy.tools.allow(methods=["POST"])
    def semantic_search(self, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        if username and password:
            self._check_auth(username=username, password=password)
        data = cherrypy.request.json
        user_input = data.get("user_input", "")
        symptoms_diseases = data.get("symptoms_diseases", [])
        semantic_similarity_cutoff = data.get("semantic_similarity_cutoff", 0.6)
        return semantic_search_snomed(
            user_input=user_input,
            symptoms_and_diseases=symptoms_diseases,
            ner_model=self.ner_model,
            ner_tokenizer=self.ner_tokenizer,
            faiss_index=self.faiss_index,
            concept_id_to_concept=self.concept_id_to_concept,
            semantic_similarity_cutoff=semantic_similarity_cutoff,
            use_cuda=False,
        )

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    @cherrypy.tools.allow(methods=["POST"])
    def follow_up(self, username: Optional[str] = None, password: Optional[str] = None) -> List[Dict]:
        if username and password:
            self._check_auth(username=username, password=password)
        data = cherrypy.request.json
        snomed_concept_ids = data.get("snomed_concept_ids", [])
        symptoms_diseases = data.get("symptoms_diseases", [])
        decoding_strategy = data.get("decoding_strategy", "generate")
        generation_params = data.get(
            "generation_params",
            {
                "temperature": 0.7,
                "do_sample": True,
                "max_new_tokens": 256,
                "exponential_decay_length_penalty": [230, 1.9],
            },
        )
        return generate_follow_up_questions_from_concepts(
            snomed_concept_ids=snomed_concept_ids,
            symptoms_diseases=symptoms_diseases,
            tokenizer=self.tokenizer,
            model=self.model,
            concept_id_to_concept=self.concept_id_to_concept,
            decoding_strategy=decoding_strategy,
            **generation_params,
        )

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    @cherrypy.tools.allow(methods=["POST"])
    def summary(self, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        if username and password:
            self._check_auth(username=username, password=password)
        data = cherrypy.request.json
        snomed_concept_ids = data.get("snomed_concept_ids", [])
        qa = data.get("qa", {})
        decoding_strategy = data.get("decoding_strategy", "generate")
        symptoms_diseases = data.get("symptoms_diseases", [])
        generation_params = data.get(
            "generation_params",
            {
                "temperature": 0.7,
                "do_sample": True,
                "max_new_tokens": 2048,
                "exponential_decay_length_penalty": [1900, 1.9],
            },
        )
        return generate_summary_from_qa(
            snomed_concept_ids=snomed_concept_ids,
            qa=qa,
            symptoms_diseases=symptoms_diseases,
            tokenizer=self.tokenizer,
            model=self.model,
            concept_id_to_concept=self.concept_id_to_concept,
            decoding_strategy=decoding_strategy,
            **generation_params,
        )

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.allow(methods=["POST"])
    def graph(self, username: Optional[str] = None, password: Optional[str] = None) -> None:
        if username and password:
            self._check_auth(username=username, password=password)
        data = cherrypy.request.json
        snomed_concepts = data.get("snomed_concepts", [])
        graph_search_depth = data.get("graph_search_depth", 1)
        result = generate_snomed_graph_from_concepts(
            snomed_concepts=snomed_concepts,
            G=self.G,
            concept_id_to_concept=self.concept_id_to_concept,
            graph_search_depth=graph_search_depth,
        )

        file_path = result[1]
        graph_text = result[2]

        if os.path.exists(file_path):
            multipart = MIMEMultipart()

            # Add the graph text
            text_part = MIMEText(graph_text, "plain")
            multipart.attach(text_part)

            # Add the file
            with open(file_path, "rb") as f:
                file_data = f.read()

            file_part = MIMEApplication(file_data, Name=os.path.basename(file_path))
            multipart.attach(file_part)

            # Convert multipart object to bytes
            multipart_bytes = multipart.as_bytes()
            log.debug(f"Multipart bytes length: {len(multipart_bytes)}")

            cherrypy.response.stream = True
            cherrypy.response.timeout = 10000
            cherrypy.response.headers["Content-Type"] = "multipart/mixed"
            cherrypy.response.headers["Content-Length"] = str(len(multipart_bytes))

            def content():
                yield multipart_bytes

            return content()

            log.debug(f"Multipart response successfully created with size {len(multipart_bytes)} bytes.")
        else:
            log.error("File does not exist.")
            raise ValueError("Server crashed")

    def listen(
        self,
        endpoint: str = "*",
        port: int = 3000,
        llm_model: str = "/run/media/ixaxaar/models_f/models/Mistral-7B-v0.1",
        ner_model: str = "emilyalsentzer/Bio_ClinicalBERT",
        networkx_graph: str = "./saved/snomed.graph",
        faiss_index: str = "./saved/faiss.index",
        concept_id_to_concept: str = "./saved/concept_id_to_concept.pickle",
        description_id_to_concept: str = "./saved/description_id_to_concept.pickle",
        cors_domain: str = "http://localhost:3000",
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.load_models(
            llm_model=llm_model,
            ner_model=ner_model,
            networkx_graph=networkx_graph,
            faiss_index=faiss_index,
            concept_id_to_concept=concept_id_to_concept,
            description_id_to_concept=description_id_to_concept,
        )

        def CORS():
            cherrypy.response.headers["Access-Control-Allow-Origin"] = "https://geniusrise.health"
            cherrypy.response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            cherrypy.response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            cherrypy.response.headers["Access-Control-Allow-Credentials"] = "true"

            if cherrypy.request.method == "OPTIONS":
                cherrypy.response.status = 200
                return True

        cherrypy.config.update(
            {
                "server.socket_host": "0.0.0.0",
                "server.socket_port": port,
                "log.screen": False,
                "tools.CORS.on": True,
            }
        )

        cherrypy.tools.CORS = cherrypy.Tool("before_handler", CORS)
        cherrypy.tree.mount(self, "/api/v1/", {"/": {"tools.CORS.on": True}})
        cherrypy.tools.CORS = cherrypy.Tool("before_finalize", CORS)
        cherrypy.engine.start()
        cherrypy.engine.block()
