#!/usr/bin/env python3

import subprocess

from flask import Flask, request, redirect, Response
from requests import get, post
import tsv2rdf

#root = "/browse/"
root = "/"
data = tsv2rdf.readdir("data2")
app = Flask(__name__, instance_relative_config=True)

@app.route('/favicon.ico')
def favicon():
    return ""

@app.route('/style.css')
def style():
    return """
#annotations {
  padding-left: 1em;
  list-style-type: none !important;
}
#annotations ul {
  padding-left: 3em;
  list-style-type: circle !important;
}
#annotations ul ul {
  padding-left: 2em;
  list-style-type: none !important;
}
#hierarchy {
  padding-left: 2.2em;
  list-style-type: circle !important;
}
#hierarchy ul {
  padding-left: 0.5em;
  list-style-type: circle !important;
}
""", 200, {"Content-Type": "text/css"}


@app.route('/')
def index():
    output = []
    for tree in sorted(data["trees"]):
        output.append(f"""<li><a href="{root}{tree}">{tree}</a>""")
    output = "\n".join(output)
    return f"<html><ul>{output}</ul></html>"


# Proxy /sqlite-web to localhost 8080
SITE_NAME="http://localhost:8080/sqlite-web/"
@app.route('/sqlite-web/', defaults={"path": ""})
@app.route('/sqlite-web/<path:path>', methods=["GET", "POST"])
def proxy(path):
    print(request)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    if request.method=='GET':
        resp = get(f'{SITE_NAME}{path}')
    elif request.method=='POST':
        resp = post(f'{SITE_NAME}{path}', request.form)
    headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    response = Response(resp.content, resp.status_code, headers)
    return response


@app.route('/<tree>')
def tree(tree):
    return redirect(root + tree + "/NCBITaxon:1")


@app.route('/<tree>/<term_id>')
def term(tree, term_id):
    return tsv2rdf.terms2rdfa(data, tree, [term_id])


if __name__ == '__main__':
    app.run(port=5006)
