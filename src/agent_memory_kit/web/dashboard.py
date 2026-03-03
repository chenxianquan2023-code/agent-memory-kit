"""
Web Dashboard for Agent Memory Kit.
FastAPI-based web interface for memory management and visualization.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import asdict

try:
    from fastapi import FastAPI, HTTPException, WebSocket
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


class MemoryDashboard:
    """
    Web dashboard for visualizing and managing agent memory.
    
    Features:
    - Real-time memory stats
    - Layer visualization (HOT/WARM/COLD)
    - Graph exploration
    - Vector search interface
    - Memory editing
    """
    
    def __init__(self, memory_manager, host="127.0.0.1", port=8787):
        if not HAS_FASTAPI:
            raise ImportError(
                "FastAPI required. Install with: pip install fastapi uvicorn"
            )
        
        self.memory = memory_manager
        self.host = host
        self.port = port
        self.app = self._create_app()
    
    def _create_app(self) -> "FastAPI":
        """Create FastAPI application."""
        app = FastAPI(
            title="Agent Memory Kit Dashboard",
            description="Visual interface for managing agent memory",
            version="0.2.0"
        )
        
        # CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Routes
        @app.get("/", response_class=HTMLResponse)
        async def root():
            return self._get_dashboard_html()
        
        @app.get("/api/stats")
        async def get_stats():
            """Get memory statistics."""
            stats = self.memory.get_stats()
            
            # Add vector stats if enabled
            if hasattr(self.memory, '_vector') and self.memory._vector:
                stats['vector'] = self.memory._vector.get_stats()
            
            # Add graph stats if enabled
            if hasattr(self.memory, '_graph') and self.memory._graph:
                stats['graph'] = self.memory._graph.get_stats()
            
            return stats
        
        @app.get("/api/memory/{layer}")
        async def get_memory_layer(layer: str, limit: int = 50):
            """Get memory entries from a specific layer."""
            if layer == "hot":
                return {"entries": self.memory._hot_cache}
            elif layer == "warm":
                entries = {}
                for key in list(self.memory._warm_cache.keys())[:limit]:
                    entries[key] = self.memory._warm_cache[key]
                return {"entries": entries}
            elif layer == "cold":
                # List cold files
                cold_files = list(self.memory.cold_dir.glob("*.json"))[:limit]
                entries = {}
                for f in cold_files:
                    with open(f) as fp:
                        entries[f.stem] = json.load(fp)
                return {"entries": entries}
            else:
                raise HTTPException(status_code=400, detail="Invalid layer")
        
        @app.post("/api/memory/{layer}/{key}")
        async def set_memory(layer: str, key: str, value: Dict):
            """Set a memory value."""
            if layer == "hot":
                self.memory.hot(key, value)
            elif layer == "warm":
                self.memory.warm(key, value)
            elif layer == "cold":
                self.memory.cold(key, value)
            else:
                raise HTTPException(status_code=400, detail="Invalid layer")
            return {"status": "ok"}
        
        @app.delete("/api/memory/{layer}/{key}")
        async def delete_memory(layer: str, key: str):
            """Delete a memory entry."""
            if layer == "hot" and key in self.memory._hot_cache:
                del self.memory._hot_cache[key]
            elif layer == "warm" and key in self.memory._warm_cache:
                del self.memory._warm_cache[key]
            # Cold deletion would need file removal
            return {"status": "ok"}
        
        @app.post("/api/vector/search")
        async def vector_search(query: Dict):
            """Search vector memory."""
            if not hasattr(self.memory, '_vector') or not self.memory._vector:
                raise HTTPException(status_code=503, detail="Vector memory not enabled")
            
            results = self.memory.vector_search(
                query.get("text", ""),
                top_k=query.get("top_k", 5)
            )
            return {"results": results}
        
        @app.get("/api/graph/entities")
        async def get_graph_entities():
            """Get all graph entities."""
            if not hasattr(self.memory, '_graph') or not self.memory._graph:
                raise HTTPException(status_code=503, detail="Graph memory not enabled")
            
            return {
                "entities": [
                    asdict(e) for e in self.memory._graph._entities.values()
                ]
            }
        
        @app.get("/api/graph/relations/{entity_id}")
        async def get_entity_relations(entity_id: str):
            """Get relations for an entity."""
            if not hasattr(self.memory, '_graph') or not self.memory._graph:
                raise HTTPException(status_code=503, detail="Graph memory not enabled")
            
            neighbors = self.memory._graph.get_neighbors(entity_id)
            return {"relations": neighbors}
        
        @app.post("/api/compress")
        async def compress_memory():
            """Trigger memory compression."""
            stats = self.memory.compress()
            return {"compressed": stats}
        
        return app
    
    def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>Agent Memory Kit Dashboard</title>
    <meta charset="utf-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            text-align: center;
        }
        .header h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .header p { opacity: 0.9; }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: #1e293b;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #334155;
        }
        .stat-card h3 {
            color: #94a3b8;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .layers-section {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .layer-card {
            background: #1e293b;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #334155;
        }
        .layer-card.hot { border-top: 4px solid #f59e0b; }
        .layer-card.warm { border-top: 4px solid #ef4444; }
        .layer-card.cold { border-top: 4px solid #3b82f6; }
        .layer-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        .memory-list {
            max-height: 300px;
            overflow-y: auto;
        }
        .memory-item {
            background: #334155;
            padding: 0.75rem;
            border-radius: 8px;
            margin-bottom: 0.5rem;
            font-family: monospace;
            font-size: 0.875rem;
            cursor: pointer;
            transition: background 0.2s;
        }
        .memory-item:hover { background: #475569; }
        .memory-key { color: #60a5fa; }
        .actions {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.2s;
        }
        .btn:hover { background: #2563eb; }
        .btn-danger { background: #ef4444; }
        .btn-danger:hover { background: #dc2626; }
        .search-box {
            background: #1e293b;
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 2rem;
        }
        .search-box input {
            width: 100%;
            padding: 0.75rem;
            background: #334155;
            border: 1px solid #475569;
            border-radius: 8px;
            color: white;
            font-size: 1rem;
        }
        .loading {
            text-align: center;
            padding: 2rem;
            color: #94a3b8;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 Agent Memory Kit Dashboard</h1>
        <p>Visual memory management and analytics</p>
    </div>
    
    <div class="container">
        <div class="stats-grid" id="stats">
            <div class="loading">Loading stats...</div>
        </div>
        
        <div class="actions">
            <button class="btn" onclick="refreshData()">🔄 Refresh</button>
            <button class="btn" onclick="compressMemory()">📦 Compress Memory</button>
            <button class="btn btn-danger" onclick="clearHot()">🗑️ Clear HOT</button>
        </div>
        
        <div class="search-box">
            <h3 style="margin-bottom: 1rem;">🔍 Vector Search</h3>
            <input type="text" id="searchInput" placeholder="Search memory semantically..." 
                   onkeypress="if(event.key==='Enter')searchVector()">
        </div>
        
        <div class="layers-section" id="layers">
            <div class="loading">Loading layers...</div>
        </div>
    </div>
    
    <script>
        async function fetchStats() {
            try {
                const res = await fetch('/api/stats');
                const stats = await res.json();
                displayStats(stats);
            } catch (e) {
                console.error('Failed to load stats:', e);
            }
        }
        
        function displayStats(stats) {
            const html = `
                <div class="stat-card">
                    <h3>⚡ HOT Entries</h3>
                    <div class="stat-value">${stats.hot_entries || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>🔥 WARM Entries</h3>
                    <div class="stat-value">${stats.warm_entries || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>❄️ COLD Entries</h3>
                    <div class="stat-value">${stats.cold_entries || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>💾 Size (MB)</h3>
                    <div class="stat-value">${stats.workspace_size_mb || 0}</div>
                </div>
            `;
            document.getElementById('stats').innerHTML = html;
        }
        
        async function fetchLayers() {
            try {
                const [hot, warm, cold] = await Promise.all([
                    fetch('/api/memory/hot').then(r => r.json()),
                    fetch('/api/memory/warm').then(r => r.json()),
                    fetch('/api/memory/cold').then(r => r.json())
                ]);
                displayLayers(hot, warm, cold);
            } catch (e) {
                console.error('Failed to load layers:', e);
            }
        }
        
        function displayLayers(hot, warm, cold) {
            const html = `
                <div class="layer-card hot">
                    <div class="layer-title">⚡ HOT Layer</div>
                    <div class="memory-list">
                        ${Object.entries(hot.entries || {}).slice(0, 10).map(([k, v]) => `
                            <div class="memory-item">
                                <span class="memory-key">${k}</span>: 
                                ${JSON.stringify(v).substring(0, 100)}...
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="layer-card warm">
                    <div class="layer-title">🔥 WARM Layer</div>
                    <div class="memory-list">
                        ${Object.entries(warm.entries || {}).slice(0, 10).map(([k, v]) => `
                            <div class="memory-item">
                                <span class="memory-key">${k}</span>: 
                                ${JSON.stringify(v).substring(0, 100)}...
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="layer-card cold">
                    <div class="layer-title">❄️ COLD Layer</div>
                    <div class="memory-list">
                        ${Object.entries(cold.entries || {}).slice(0, 10).map(([k, v]) => `
                            <div class="memory-item">
                                <span class="memory-key">${k}</span>: 
                                ${JSON.stringify(v).substring(0, 100)}...
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.getElementById('layers').innerHTML = html;
        }
        
        async function refreshData() {
            await Promise.all([fetchStats(), fetchLayers()]);
        }
        
        async function compressMemory() {
            await fetch('/api/compress', { method: 'POST' });
            refreshData();
        }
        
        async function clearHot() {
            if (confirm('Clear all HOT memory?')) {
                await fetch('/api/memory/hot', { method: 'DELETE' });
                refreshData();
            }
        }
        
        async function searchVector() {
            const query = document.getElementById('searchInput').value;
            if (!query) return;
            
            const res = await fetch('/api/vector/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: query, top_k: 5})
            });
            const data = await res.json();
            alert('Search results: ' + JSON.stringify(data.results, null, 2));
        }
        
        // Initial load
        refreshData();
        
        // Auto-refresh every 10 seconds
        setInterval(refreshData, 10000);
    </script>
</body>
</html>
        '''
    
    def run(self):
        """Run the dashboard server."""
        import uvicorn
        print(f"🌐 Starting Memory Dashboard at http://{self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port)


def launch_dashboard(memory_manager, port: int = 8787):
    """
    Quick launch function for the dashboard.
    
    Usage:
        from agent_memory_kit import MemoryManager
        from agent_memory_kit.web.dashboard import launch_dashboard
        
        memory = MemoryManager("./my_workspace")
        launch_dashboard(memory)
    """
    dashboard = MemoryDashboard(memory_manager, port=port)
    dashboard.run()
