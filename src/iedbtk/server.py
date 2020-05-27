#!/usr/bin/env python3
import math
import sqlite3
import subprocess

from copy import deepcopy
from flask import Flask, request, redirect, Response, render_template
from requests import get, post
from urllib.parse import urlencode
import tsv2rdf

#root = "/browse/"
root = "/"
data = tsv2rdf.readdir("data2")
sqlite = "file:build/iedb.db?mode=ro"
app = Flask(__name__, instance_relative_config=True)

limit = 25

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
  list-style-type: none !important;
}
#hierarchy ul {
  padding-left: 1em;
  list-style-type: none !important;
  border-left: 1px dashed #ddd;
}
""", 200, {"Content-Type": "text/css"}


@app.route('/')
def index():
    html = ["div",
            ["p", ["a", {"href": "/search/"}, "Search"]],
            #["p", ["a", {"href": "/sqlite-web/"}, "SQL Browser"]]
            ]
    return render_template("base.jinja2", html=tsv2rdf.render(html))

links = {
    "reference_id": "http://iedb.org/reference/",
    "assay_id": "http://iedb.org/assay/",
    "epitope_id": "http://iedb.org/epitope/",
    "structure_id": "http://iedb.org/epitope/",
    "pubmed_id": "https://pubmed.ncbi.nlm.nih.gov/",
}

def make_page(args, page, string):
    args = args.copy()
    cls = "page-item"
    if args["page"] == page:
        cls += " disabled"
    args["page"] = page
    return ["li",
            {"class": cls},
            ["a",
             {"class": "page-link", "href": "?" + urlencode(args)},
             string]]


def make_paged_table(rows, count, args):
    page = int(args.get("page", "1"))
    last = math.ceil(count/limit)
    args["page"] = page
    html = ["div"]
    nav = ["ul", {"class": "pagination justify-content-center", "style": "margin-top: 1em"}]

    nav.append(make_page(args, 1, "first"))
    nav.append(make_page(args, max(1, page - 1), "prev"))

    js = f"javascript:jump({page})"
    nav.append(["li", {"class": "page-item"}, ["a", {"class": "page-link", "href": js}, f"page {page} of {last}"]])

    nav.append(make_page(args, min(last, page + 1), "next"))
    nav.append(make_page(args, last, "last"))

    html.append(nav)
    html.append(make_table(rows))
    return html


def make_table(rows):
    if not rows:
        return "No data"
    table = ["table", {"class": "table table-borderless"}]
    tr = ["tr"]
    for key in rows[0].keys():
        tr.append(["th", key])
    table.append(tr)
    for row in rows:
        tr = ["tr"]
        for key, value in row.items():
            value = str(value)
            if value and len(value) > 100:
                value = value[0:100] + "..."
            if key in links and links[key].startswith("http"):
                tr.append(["td", ["a", {"href": links[key] + value, "target": "_blank"}, value]])
            elif key in links:
                tr.append(["td", ["a", {"href": links[key] + value}, value]])
            else:
                tr.append(["td", str(value)])
        table.append(tr)
    return table

counts = {}

def my_count(cur, args):
    result = {
        "search": {"title": "Search"},
        "epitope": {"title": "Epitopes", "count": 1},
        "antigen": {"title": "Antigens", "count": 2},
        "assay": {"title": "Assays", "count": 3},
        "receptor": {"title": "Receptor", "count": -1},
        "reference": {"title": "References", "count": 5},
    }

    withs = []
    froms = ["search"]
    joins = []
    wheres = []
    if "sequence" in args and args["sequence"]:
        wheres.append(f"linear_sequence = '{args['sequence']}'")
    if "nonpeptide" in args and args["nonpeptide"]:
        ids = args["nonpeptide"].split()
        values = ", ".join([f"('{i}')" for i in ids])
        withs.append(f"""
WITH RECURSIVE nonpeptides(n) AS (
  VALUES {values}
  UNION
  SELECT child FROM nonpeptide, nonpeptides
  WHERE parent = n)""")
        joins.append("JOIN nonpeptides n ON n.n = search.non_peptide_id")

    q = {
      "with": withs,
      "select": [
          "count(distinct structure_id) AS epitope_count",
          "count(distinct source_antigen_id) AS antigen_count",
          "count(distinct assay_id) AS assay_count",
          "count(distinct reference_id) AS reference_count",
      ],
      "from": froms,

      "join": joins,
      "where": wheres
    }
    result["search"].update(q)

    # Cache the counts
    qs = build_query(q)
    print(qs)
    if qs in counts:
        return counts[qs]

    cur.execute(qs)
    row = cur.fetchone()
    result["epitope"]["count"] = row["epitope_count"]
    result["antigen"]["count"] = row["antigen_count"]
    result["assay"]["count"] = row["assay_count"]
    result["reference"]["count"] = row["reference_count"]
    counts[qs] = result
    return result


def href(args, **kwargs):
    d = {}
    d.update(args)
    d.update(kwargs)
    return "?" + urlencode(d)

def build_query(q):
    result = ""
    if "with" in q and q["with"]:
        result += "\n".join(q["with"])
    result += "\nSELECT\n  "
    result += ",\n  ".join(q["select"])
    result += "\nFROM "
    result += ", ".join(q["from"])
    if "join" in q and q["join"]:
        result += "\n" + "\n".join(q["join"])
    if "where" in q and q["where"]:
        result += "\nWHERE " + "\n  AND".join(q["where"])
    if "group by" in q and q["group by"]:
        result += "\nGROUP BY " + ", ".join(q["group by"])
    if "order by" in q and q["order by"]:
        result += "\nORDER BY " + ", ".join(q["order by"])
    if "limit" in q and q["limit"]:
        result += f"\nLIMIT {q['limit']}"
    if "offset" in q and q["offset"]:
        result += f"\nOFFSET {q['offset']}"
    return result


def query(cur, q):
    qs = build_query(q)
    print(qs)
    return cur.execute(qs)


def build_tree(tree, root, args, content):
    if root in tree:
        result = ["li", ["a", {"href": href(args, nonpeptide=root)}, tree[root]["label"] if root in tree else root]]
        for child in tree[root]["children"]:
            result.append(build_tree(tree, child, args, content))
        return ["ul", result]
    else:
        return deepcopy(content)


@app.route('/search/')
def search():
    with sqlite3.connect(sqlite, uri=True) as conn:
        conn.row_factory = dict_factory
        cur = conn.cursor()
        html = ["div", ["h2", "Search"]]
        nav = ["ul", {"class": "nav nav-tabs justify-content-center", "style": "margin-bottom: 1em"}]
        tab = request.args.get("tab", "search")
        page = int(request.args.get("page", "1"))
        args = request.args.copy()
        args["page"] = 1
        result = my_count(cur, request.args)
        count = result[tab].get("count", 0)
        q = result["search"]
        q["limit"] = limit
        q["offset"] = offset = (page - 1) * limit

        for table, values in result.items():
            cls = "nav-link"
            if tab == table:
                cls += " active"
            args["tab"] = table
            title = values["title"]
            if "count" in values:
                title += f" ({values['count']})"
            nav.append(
               ["li",
                {"class": "nav-item"}, 
                ["a",
                 {"class": cls, "href": "?" + urlencode(args)},
                 title]])
        html.append(nav)

        args = request.args.copy()
        if tab == "search":
            form = ["form",
                    {"id": "search-form"},
                    ["p",
                     ["a", {"class": "btn btn-primary", "href": "/search/"}, "Clear"],
                     ["input", {"class": "btn btn-success", "type": "submit", "value": "Search"}]],
                    ["p", "structure type list"],
                    ["p",
                     ["label", {"for": "sequence"}, "Epitope linear sequence"],
                     ["input", {"id": "sequence", "name": "sequence", "type": "text", "placeholder": "SIINFEKL", "value": request.args.get("sequence", "")}]],
                    ["p", "non-peptidic epitope finder"],
                    ["p",
                     ["label", {"for": "nonpeptide"}, "Non-Peptic Epitope"],
                     ["input", {"id": "nonpeptide", "name": "nonpeptide", "type": "text", "placeholder": "CHEBI:28112", "value": request.args.get("nonpeptide", "")}]],
                    ["p", "organism finder"],
                    ["p", "antigen finder"],
                    ["p", "mhc finder"],
                    ["p", "host finder"],
                    ["p", "disease finder"],
                    ["p", "qualitative measure"]]
            nonpeptide = args.get("nonpeptide","IEDB:non-peptidic-material").split()[0]

            cur.execute(f"""SELECT DISTINCT child, label
                    FROM nonpeptide
                    JOIN label ON child = id
                    WHERE parent = '{nonpeptide}'
                    ORDER BY sort""")
            children = ["ul"]
            for row in cur:
                children.append(["li", ["a", {"href": href(args, nonpeptide=row["child"])}, row["label"]]])

            cur.execute(f"""WITH RECURSIVE ancestors(p, c, s) AS (
                VALUES ('{nonpeptide}', NULL, 0)
                UNION
                SELECT parent, child, sort FROM nonpeptide, ancestors WHERE child = p
              )
              SELECT DISTINCT p AS parent, c AS child, s AS sort, label
              FROM ancestors JOIN label ON p = id""")
            rows = cur.fetchall()
            current = rows.pop(0)
            ancestors = ["ul",
                         ["li",
                          ["a", {"href": href(args, nonpeptide=nonpeptide)}, current["label"]],
                          children]]
            tree = {}
            for row in rows:
                parent = row["parent"]
                if not parent in tree:
                    tree[parent] = {"label": row["label"], "children": {row["child"]}}
                else:
                    tree[parent]["children"].add(row["child"])
            root = "IEDB:non-peptidic-material"
            content = ["li", current["label"]]
            if children and len(children) > 1:
                content.append(children)
            content = ["ul", content]
            tree = build_tree(tree, root, args, content)
            tree.insert(1, {"id": "hierarchy", "class": "col-md"})
            html.append(["div",
                         {"class": "row"},
                         ["div", {"class": "col"}, form], 
                         tree])

        elif tab == "epitope":
            q["select"] = [
                "structure_id",
                "description",
                "source_antigen_label",
                "source_organism_label",
                "count(distinct assay_id) AS assays",
                "count(distinct reference_id) AS \"references\""
            ]
            q["group by"] = ["structure_id"]

        elif tab == "antigen":
            q["select"] = [
                "source_antigen_label",
                "source_antigen_source_organism_label",
                "count(distinct structure_id) AS epitopes",
                "count(distinct assay_id) AS assays",
                "count(distinct reference_id) AS \"references\"",
            ]
            q["group by"] = ["source_antigen_id"]

        elif tab == "assay":
            q["select"] = [
                "DISTINCT assay_id",
                "reference_id",
                "assay_type_id"
            ]

        elif tab == "reference":
            q["select"] = [
                "DISTINCT reference_id",
                "pubmed_id",
                "reference_author",
                "reference_title",
                "reference_date"
            ]

        if tab != "search":
            query(cur, q)
            html.append(make_paged_table(cur.fetchall(), count, dict(request.args)))

        return render_template("base.jinja2", html=tsv2rdf.render(html))


# Proxy /sqlite-web to localhost 8080
SITE_NAME="http://localhost:8080/sqlite-web/"
@app.route('/sqlite-web/', defaults={"path": ""})
@app.route('/sqlite-web/<path:path>', methods=["GET", "POST"])
def proxy(path):
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
    app.run(port=5005)
