"""
Stub of the bobntay parse API, used by test_fetch_song.sh to drive
scripts/fetch_song.sh through its retry and exit-code paths without a server,
a database or a network round trip to Genius.

Binds an ephemeral port and writes the chosen port number to PORT_FILE, so
concurrent runs cannot collide.

Env:
  PORT_FILE     path to write the bound port number to
  NEXT_CODES    comma-separated statuses returned by GET /parse/next-song/
  PAGE_CODES    comma-separated statuses returned by GET /page
  SUBMIT_CODES  comma-separated statuses returned by POST /parse/submit-page/
  SUBMIT_BODY   "json" (default) or "html", to return a 422 that is not JSON
  REPORT_CODES  comma-separated statuses returned by POST /parse/report-page-failure/
                (404 stands in for a server deployed before that endpoint existed)

Each list is consumed in order and its final entry repeats once exhausted, so
SUBMIT_CODES=422 means "reject everything" and SUBMIT_CODES=422,200 means
"reject the first candidate, accept the second".
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


def status_codes(name, default):
    return [int(code) for code in os.environ.get(name, default).split(",")]


NEXT_CODES = status_codes("NEXT_CODES", "200")
PAGE_CODES = status_codes("PAGE_CODES", "200")
SUBMIT_CODES = status_codes("SUBMIT_CODES", "200")
REPORT_CODES = status_codes("REPORT_CODES", "200")
SUBMIT_BODY = os.environ.get("SUBMIT_BODY", "json")

served = {"next": 0, "page": 0, "submit": 0, "report": 0}


def next_status(key, code_list):
    index = min(served[key], len(code_list) - 1)
    served[key] += 1
    return code_list[index]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        """Silence the default per-request logging; the test reads the script's output."""

    def respond(self, code, body, content_type="application/json"):
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path.startswith("/parse/next-song/"):
            code = next_status("next", NEXT_CODES)
            if code != 200:
                self.respond(code, json.dumps({"detail": f"stub {code}"}))
                return

            # A fresh candidate each time, so a retry is visibly a different track.
            candidate = served["next"]
            self.respond(
                200,
                json.dumps(
                    {
                        "track": {
                            "id": 1000 + candidate,
                            "title": f"Candidate {candidate}",
                            "primary_artist_names": "Stub Artist",
                            "api_path": f"/songs/{1000 + candidate}",
                            "url": f"http://localhost:{PORT}/page",
                        },
                        "genius_record": {"id": 1000 + candidate, "writer_artists": []},
                    }
                ),
            )
        elif self.path.startswith("/page"):
            self.respond(
                next_status("page", PAGE_CODES),
                "<html><body>lyrics</body></html>",
                "text/html",
            )
        else:
            self.respond(404, json.dumps({"detail": "unknown path"}))

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))

        if self.path.startswith("/parse/report-page-failure/"):
            self.report_page_failure()
            return

        code = next_status("submit", SUBMIT_CODES)

        if code == 200:
            self.respond(200, json.dumps({"detail": 'Saved "Candidate" by Stub Artist.'}))
        elif code == 422 and SUBMIT_BODY == "html":
            self.respond(422, "<html><body>Gateway Error</body></html>", "text/html")
        elif code == 422:
            self.respond(422, json.dumps({"detail": "Tagged Non-Music.", "rejected": True}))
        else:
            self.respond(code, json.dumps({"detail": f"stub {code}"}))

    def report_page_failure(self):
        code = next_status("report", REPORT_CODES)

        if code == 200:
            self.respond(
                200,
                json.dumps({"detail": "Genius page no longer exists", "rejected": True}),
            )
        elif code == 400:
            self.respond(
                400,
                json.dumps(
                    {
                        "detail": "Status 403 is not a permanent failure; no rejection recorded.",
                        "rejected": False,
                    }
                ),
            )
        else:
            # 404 stands in for a server deployed before this endpoint existed;
            # Django answers an unknown route with an HTML debug page, not JSON.
            self.respond(code, "<html><body>Not Found</body></html>", "text/html")


server = HTTPServer(("127.0.0.1", 0), Handler)
PORT = server.server_address[1]

with open(os.environ["PORT_FILE"], "w") as port_file:
    port_file.write(str(PORT))

server.serve_forever()
