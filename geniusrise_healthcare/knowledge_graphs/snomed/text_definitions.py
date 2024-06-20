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
from tqdm import tqdm
import networkx as nx

log = logging.getLogger(__name__)


def process_text_definition_file(text_definition_file: str, G: nx.DiGraph) -> None:
    """
    Processes the SNOMED CT text definition file and maps concept IDs to their text definitions.

    Args:
        text_definition_file (str): Path to the text definition file.

    Returns:
        None
    """
    with open(text_definition_file, "r", newline='') as f:
        num_lines = sum(1 for _ in f)

    log.info(f"Loading text definitions from {text_definition_file}")
    with open(text_definition_file, "r") as f:  # type: ignore
        reader = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)  # type: ignore
        next(reader)
        for row in tqdm(reader, total=num_lines):
            try:
                concept_id, active, term, definition_type, case_significance = (
                    row[4],
                    row[2],
                    row[7],
                    row[6],
                    row[8],
                )
                if active == "1":
                    attrs = {
                        int(concept_id): {
                            "term": term,
                            "definition_type": definition_type,
                            "case_significance": case_significance,
                        }
                    }
                    nx.set_node_attributes(G, attrs)

            except Exception as e:
                log.error(f"Error processing text definition {row}: {e}")
                raise ValueError(f"Error processing text definition {row}: {e}")
