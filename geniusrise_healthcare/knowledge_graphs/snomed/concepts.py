# 🧠 Geniusrise
# Copyright (C) 2023  geniusrise.ai
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import csv
import logging
import sys
from typing import List

import networkx as nx
import numpy as np
from tqdm import tqdm

from .util import extract_and_remove_semantic_tag

log = logging.getLogger(__name__)


def process_concept_file(concept_file: str, G: nx.DiGraph) -> None:
    """
    Processes the SNOMED CT concept file and adds concepts to the graph.

    Args:
        concept_file (str): Path to the concept file.
        G (nx.DiGraph): NetworkX graph to which the concepts will be added.

    Returns:
        None
    """
    batch_ids: List[int] = []

    csv.field_size_limit(sys.maxsize)

    with open(concept_file, "r", newline='') as f:
        num_lines = sum(1 for _ in f)

    log.info(f"Loading concepts from {concept_file}")
    with open(concept_file, "r") as f:  # type: ignore
        reader = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)  # type: ignore
        next(reader)
        for row in tqdm(reader, total=num_lines):
            try:
                (
                    description_id,
                    active,
                    definition_status,
                    concept_id,
                    language,
                    type_id,
                    concept_name,
                    case_significance,
                ) = (
                    row[0],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    row[8],
                )

                if active == "1" and language == "en":
                    semantic_tag, fsn_without_tag = extract_and_remove_semantic_tag(concept_name.lower())
                    G.add_node(
                        int(concept_id),
                        type=type_id,
                        tag=semantic_tag,
                        definition_status=definition_status,
                        case_significance=case_significance,
                    )

            except Exception as e:
                log.error(f"Error processing node {row}: {e}")
                raise ValueError(f"Error processing node {row}: {e}")
