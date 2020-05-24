#!/usr/bin/env python3

import sqlite3
import subprocess

from flask import Flask, request, redirect, Response, render_template
from requests import get, post
import tsv2rdf

#root = "/browse/"
root = "/"
data = tsv2rdf.readdir("data2")
sqlite = "file:build/iedb.db?mode=ro"
app = Flask(__name__, instance_relative_config=True)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

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
    html = ["div",
            ["p", ["a", {"href": "/reference/"}, "References"]],
            ["p", ["a", {"href": "/sqlite-web/"}, "SQL Browser"]]]
    return render_template("base.jinja2", html=tsv2rdf.render(html))


@app.route('/reference/')
def references():
    with sqlite3.connect(sqlite, uri=True) as conn:
        conn.row_factory = dict_factory
        cur = conn.cursor()
        cur.execute("""SELECT r.reference_id, a.article_title
          FROM reference r
          LEFT JOIN article a ON a.reference_id = r.reference_id
          ORDER BY r.reference_id""")
        items = []
        for row in cur:
            items.append(["li",
                ["a",
                 {"href": row["reference_id"]},
                 row["reference_id"]],
                " " + (row["article_title"] or "Submission")])
        html = ["div",
                ["h2", "References"],
                ["ul"] + items]
        return render_template("base.jinja2", html=tsv2rdf.render(html))


@app.route('/reference/<reference_id>')
def reference(reference_id):
    with sqlite3.connect(sqlite, uri=True) as conn:
        conn.row_factory = dict_factory
        cur = conn.cursor()
        html = ["div", ["h2", ["a", {"href": "./"}, "References"]]]

        cur.execute(f"SELECT * FROM reference WHERE reference_id = '{reference_id}'")
        rows = cur.fetchall()
        items = []
        for key, value in rows[0].items():
            items.append(["li", ["strong", key], ": ", value])
        items = ["ul", {"style": "list-style: none"}] + items
        html.append(["h3", f"Reference {reference_id}"])
        html.append(items)

        cur.execute(f"SELECT * FROM article WHERE reference_id = '{reference_id}'")
        rows = cur.fetchall()
        items = []
        for key, value in rows[0].items():
            items.append(["li", ["strong", key], ": ", value])
        items = ["ul", {"style": "list-style: none"}] + items
        html.append(["h3", f"Article"])
        html.append(items)

        return render_template("base.jinja2", html=tsv2rdf.render(html))


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
