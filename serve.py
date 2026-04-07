import http.server
import os

os.chdir(os.path.join(os.path.dirname(__file__), "frontend", "public"))
handler = http.server.SimpleHTTPRequestHandler
server = http.server.HTTPServer(("0.0.0.0", 3000), handler)
print("Server running at http://localhost:3000")
server.serve_forever()
