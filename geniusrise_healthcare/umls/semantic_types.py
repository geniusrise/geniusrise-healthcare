# 🧠 Geniusrise
# Copyright (C) 2023  geniusrise.ai
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import csv
import logging

import networkx as nx
from tqdm import tqdm

log = logging.getLogger(__name__)


def process_semantic_types_file(semantic_types_file: str, G: nx.DiGraph) -> None:
    """
    Processes the UMLS semantic types file (MRSTY.RRF) and adds the semantic types to the graph.

    Args:
        semantic_types_file (str): Path to the UMLS semantic types file (MRSTY.RRF).
        G (nx.DiGraph): The NetworkX graph to which the semantic types will be added.

    Returns:
        None
    """
    log.info(f"Loading semantic types from {semantic_types_file}")

    with open(semantic_types_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="|")
        for row in tqdm(reader):
            try:
                cui, tui = row[0], row[1]
                if cui in G:
                    if "semantic_types" not in G.nodes[cui]:
                        G.nodes[cui]["semantic_types"] = []
                    G.nodes[cui]["semantic_types"].append(tui)
            except Exception as e:
                log.error(f"Error processing semantic type {row}: {e}")
                raise ValueError(f"Error processing semantic type {row}: {e}")