"""
Knowledge graph for memory relationships.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import networkx as nx


@dataclass
class Entity:
    """A node in the knowledge graph."""
    id: str
    type: str  # person, concept, event, document, etc.
    name: str
    properties: Dict[str, Any]


@dataclass
class Relation:
    """An edge in the knowledge graph."""
    source: str  # entity ID
    target: str  # entity ID
    type: str    # wrote, cites, related_to, part_of, etc.
    properties: Dict[str, Any]


class MemoryGraph:
    """
    Knowledge graph for memory relationships.
    
    Features:
    - Entity-relation storage
    - Graph traversal queries
    - Path finding
    - Automatic relation inference
    - Graph visualization export
    """
    
    def __init__(self, workspace: str):
        self.workspace = Path(workspace) / "graph"
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        self.entities_file = self.workspace / "entities.json"
        self.relations_file = self.workspace / "relations.json"
        
        # In-memory graph
        self._graph = nx.DiGraph()
        self._entities: Dict[str, Entity] = {}
        
        self._load_graph()
    
    def _load_graph(self):
        """Load graph from disk."""
        # Load entities
        if self.entities_file.exists():
            with open(self.entities_file, 'r') as f:
                data = json.load(f)
                for e_data in data.get("entities", []):
                    entity = Entity(**e_data)
                    self._entities[entity.id] = entity
                    self._graph.add_node(entity.id, **asdict(entity))
        
        # Load relations
        if self.relations_file.exists():
            with open(self.relations_file, 'r') as f:
                data = json.load(f)
                for r_data in data.get("relations", []):
                    relation = Relation(**r_data)
                    self._graph.add_edge(
                        relation.source, 
                        relation.target,
                        **asdict(relation)
                    )
    
    def add_entity(self, entity_id: str, entity_type: str, 
                   name: str, properties: Optional[Dict] = None) -> Entity:
        """
        Add an entity to the graph.
        
        Args:
            entity_id: Unique ID
            entity_type: Type (person, concept, event, etc.)
            name: Display name
            properties: Additional properties
            
        Returns:
            Created entity
        """
        entity = Entity(
            id=entity_id,
            type=entity_type,
            name=name,
            properties=properties or {}
        )
        
        self._entities[entity_id] = entity
        self._graph.add_node(entity_id, **asdict(entity))
        self._persist()
        
        return entity
    
    def add_relation(self, source: str, target: str, 
                     relation_type: str, 
                     properties: Optional[Dict] = None) -> Relation:
        """
        Add a relation between entities.
        
        Args:
            source: Source entity ID
            target: Target entity ID
            relation_type: Type of relation
            properties: Additional properties
            
        Returns:
            Created relation
        """
        # Auto-create entities if they don't exist
        if source not in self._entities:
            self.add_entity(source, "unknown", source)
        if target not in self._entities:
            self.add_entity(target, "unknown", target)
        
        relation = Relation(
            source=source,
            target=target,
            type=relation_type,
            properties=properties or {}
        )
        
        self._graph.add_edge(source, target, **asdict(relation))
        self._persist()
        
        return relation
    
    def find_path(self, source: str, target: str, 
                  max_depth: int = 3) -> Optional[List[Dict]]:
        """
        Find connection path between two entities.
        
        Args:
            source: Starting entity ID
            target: Target entity ID
            max_depth: Maximum path length
            
        Returns:
            List of path steps, or None if no path
        """
        if source not in self._graph or target not in self._graph:
            return None
        
        try:
            path = nx.shortest_path(
                self._graph, 
                source, 
                target,
                cutoff=max_depth
            )
            
            # Convert to detailed steps
            steps = []
            for i in range(len(path) - 1):
                src = path[i]
                tgt = path[i + 1]
                edge_data = self._graph.edges[src, tgt]
                
                steps.append({
                    "from": self._entities[src].name,
                    "to": self._entities[tgt].name,
                    "relation": edge_data.get("type", "related_to"),
                    "from_id": src,
                    "to_id": tgt
                })
            
            return steps
        except nx.NetworkXNoPath:
            return None
    
    def get_neighbors(self, entity_id: str, 
                      relation_type: Optional[str] = None,
                      depth: int = 1) -> List[Dict]:
        """
        Get neighboring entities.
        
        Args:
            entity_id: Center entity
            relation_type: Filter by relation type
            depth: How many hops (1 = direct neighbors)
            
        Returns:
            List of neighbor entities with relation info
        """
        if entity_id not in self._graph:
            return []
        
        neighbors = []
        
        if depth == 1:
            # Direct neighbors
            for neighbor_id in self._graph.neighbors(entity_id):
                edge_data = self._graph.edges[entity_id, neighbor_id]
                
                if relation_type and edge_data.get("type") != relation_type:
                    continue
                
                neighbors.append({
                    "entity": asdict(self._entities[neighbor_id]),
                    "relation": edge_data.get("type", "related_to"),
                    "properties": edge_data.get("properties", {})
                })
        else:
            # Multi-hop using BFS
            visited = {entity_id}
            current_level = {entity_id}
            
            for _ in range(depth):
                next_level = set()
                for node in current_level:
                    for neighbor in self._graph.neighbors(node):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            next_level.add(neighbor)
                            
                            edge_data = self._graph.edges[node, neighbor]
                            if relation_type and edge_data.get("type") != relation_type:
                                continue
                            
                            neighbors.append({
                                "entity": asdict(self._entities[neighbor]),
                                "relation": edge_data.get("type", "related_to"),
                                "via": node,
                                "distance": _ + 1
                            })
                current_level = next_level
        
        return neighbors
    
    def infer_relations(self, entity_id: str) -> List[Dict]:
        """
        Infer new relations based on graph structure.
        
        Example: If A cites B, and B cites C, then A indirectly relates to C.
        
        Returns:
            List of inferred relations
        """
        if entity_id not in self._graph:
            return []
        
        inferred = []
        
        # Find two-hop connections
        neighbors_1 = list(self._graph.neighbors(entity_id))
        
        for n1 in neighbors_1:
            neighbors_2 = list(self._graph.neighbors(n1))
            for n2 in neighbors_2:
                if n2 != entity_id and n2 not in neighbors_1:
                    # This is a potential inferred relation
                    inferred.append({
                        "source": entity_id,
                        "target": n2,
                        "via": n1,
                        "type": "indirectly_related",
                        "confidence": 0.5  # Lower confidence for inferred
                    })
        
        return inferred
    
    def find_clusters(self) -> Dict[str, List[str]]:
        """
        Find communities/clusters in the graph.
        
        Returns:
            Dict mapping cluster ID to list of entity IDs
        """
        if len(self._graph) < 3:
            return {"all": list(self._entities.keys())}
        
        # Convert to undirected for community detection
        undirected = self._graph.to_undirected()
        
        # Use Louvain algorithm for community detection
        try:
            import community as community_louvain
            partition = community_louvain.best_partition(undirected)
            
            clusters = defaultdict(list)
            for node, cluster_id in partition.items():
                clusters[f"cluster_{cluster_id}"].append(node)
            
            return dict(clusters)
        except ImportError:
            # Fallback: simple connected components
            components = list(nx.connected_components(undirected))
            return {f"cluster_{i}": list(comp) for i, comp in enumerate(components)}
    
    def get_central_entities(self, top_k: int = 10) -> List[Dict]:
        """
        Find most central/important entities using PageRank.
        
        Returns:
            List of entities with centrality scores
        """
        if len(self._graph) < 2:
            return []
        
        # Compute PageRank
        pagerank = nx.pagerank(self._graph)
        
        # Sort by score
        sorted_entities = sorted(
            pagerank.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        return [
            {
                "entity": asdict(self._entities[entity_id]),
                "centrality": score
            }
            for entity_id, score in sorted_entities
        ]
    
    def query(self, pattern: Dict[str, Any]) -> List[Dict]:
        """
        Query graph with pattern matching.
        
        Args:
            pattern: Query pattern
                {"type": "person", "relation": "wrote", "target_type": "document"}
                
        Returns:
            Matching subgraphs
        """
        results = []
        
        # Simple pattern matching
        for node_id, node_data in self._graph.nodes(data=True):
            # Match source entity
            if pattern.get("type") and node_data.get("type") != pattern["type"]:
                continue
            
            # Check outgoing relations
            for neighbor_id in self._graph.neighbors(node_id):
                neighbor_data = self._graph.nodes[neighbor_id]
                edge_data = self._graph.edges[node_id, neighbor_id]
                
                # Match relation type
                if pattern.get("relation") and edge_data.get("type") != pattern["relation"]:
                    continue
                
                # Match target type
                if pattern.get("target_type") and neighbor_data.get("type") != pattern["target_type"]:
                    continue
                
                results.append({
                    "source": asdict(self._entities[node_id]),
                    "relation": edge_data.get("type"),
                    "target": asdict(self._entities[neighbor_id])
                })
        
        return results
    
    def export_graphml(self, output_path: str):
        """Export graph to GraphML format for visualization."""
        nx.write_graphml(self._graph, output_path)
    
    def export_json(self) -> Dict:
        """Export graph as JSON."""
        return {
            "entities": [asdict(e) for e in self._entities.values()],
            "relations": [
                {
                    "source": u,
                    "target": v,
                    **data
                }
                for u, v, data in self._graph.edges(data=True)
            ]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "num_entities": len(self._entities),
            "num_relations": self._graph.number_of_edges(),
            "density": nx.density(self._graph),
            "is_connected": nx.is_weakly_connected(self._graph) if len(self._graph) > 0 else False,
            "avg_degree": sum(dict(self._graph.degree()).values()) / len(self._graph) if len(self._graph) > 0 else 0
        }
    
    def _persist(self):
        """Save graph to disk."""
        # Save entities
        entities_data = {
            "entities": [asdict(e) for e in self._entities.values()]
        }
        with open(self.entities_file, 'w') as f:
            json.dump(entities_data, f, indent=2)
        
        # Save relations
        relations_data = {
            "relations": [
                {
                    "source": u,
                    "target": v,
                    **{k: v for k, v in data.items() if k not in ['source', 'target']}
                }
                for u, v, data in self._graph.edges(data=True)
            ]
        }
        with open(self.relations_file, 'w') as f:
            json.dump(relations_data, f, indent=2)
