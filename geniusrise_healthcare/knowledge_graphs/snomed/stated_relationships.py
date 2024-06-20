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

import networkx as nx
from tqdm import tqdm

log = logging.getLogger(__name__)


def process_stated_relationship_file(stated_relationship_file: str, G: nx.DiGraph) -> None:
    """
    Processes the SNOMED CT stated relationship file and adds the relationships to the graph.

    Args:
        stated_relationship_file (str): Path to the stated relationship file.
        G (nx.DiGraph): The NetworkX graph to which the relationships will be added.

    Returns:
        None
    """
    with open(stated_relationship_file, "r", newline='') as f:
        num_lines = sum(1 for _ in f)

    log.info(f"Loading stated relationships from {stated_relationship_file}")
    with open(stated_relationship_file, "r") as f:  # type: ignore
        reader = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)  # type: ignore
        next(reader)
        for row in tqdm(reader, total=num_lines):
            try:
                source_id, dest_id, active, relationship_type, relationship_group, characteristic_type, refinability = (
                    row[4],
                    row[5],
                    row[2],
                    row[7],
                    row[6],
                    row[8],
                    row[9],
                )
                if active == "1":
                    G.add_edge(
                        int(source_id),
                        int(dest_id),
                        relationship_type=relationship_type,
                        relationship_group=relationship_group,
                        characteristic_type=characteristic_type,
                        refinability=refinability,
                    )
            except Exception as e:
                log.error(f"Error processing stated relationship {row}: {e}")
                raise ValueError(f"Error processing stated relationship {row}: {e}")
