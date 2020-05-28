#!/usr/bin/env python3
import math
import sqlite3
import subprocess

from copy import deepcopy
from flask import Flask, request, redirect, Response, render_template, jsonify
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


@app.route('/')
def index():
    html = ["div",
            ["h1", "IEDBTK: Immune Epitope Database Toolkit"],
            ["p",
             "Prototype of new tools for working with data from the ",
             ["a", {"href": "http://iedb.org"}, "Immune Epitope Database"],
             "."],
            ["ul",
             ["li", ["a", {"href": "/search/?positive_assays_only=true"}, "Search"]],
             ["li", ["a", {"href": "/sqlite-web/"}, "SQL Browser"]]]]
    return render_template("base.jinja2", html=tsv2rdf.render(html))

links = {
    "reference_id": "http://iedb.org/reference/",
    "assay_id": "http://iedb.org/assay/",
    "bcell_id": "http://iedb.org/assay/",
    "tcell_id": "http://iedb.org/assay/",
    "elution_id": "http://iedb.org/assay/",
    "epitope_id": "http://iedb.org/epitope/",
    "structure_id": "http://iedb.org/epitope/",
    "receptor_id": "http://iedb.org/receptor/",
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
            if value is None:
                tr.append(["td"])
                continue
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
        "epitope": {"title": "Epitopes"},
        "antigen": {"title": "Antigens"},
        "assay": {"title": "Assays"},
        "receptor": {"title": "Receptors"},
        "reference": {"title": "References"},
    }

    withs = []
    froms = ["search AS s"]
    joins = []
    wheres = []
    if "positive_assays_only" in args and args["positive_assays_only"].lower() == "true":
        wheres.append("assay_positive IS TRUE")
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
        joins.append("JOIN nonpeptides n ON n.n = s.non_peptide_id")

    search_dict = {
      "with": withs,
      "select": [
          "count(distinct structure_id) AS epitope_count",
          "count(distinct source_antigen_label) AS antigen_count",
          "count(distinct tcell_id) AS tcell_count",
          "count(distinct bcell_id) AS bcell_count",
          "count(distinct elution_id) AS elution_count",
          "count(distinct reference_id) AS reference_count",
      ],
      "from": froms,
      "join": joins,
      "where": wheres
    }
    result["search"].update(search_dict)

    tcr_dict = deepcopy(search_dict)
    tcr_dict["select"] = ["count(distinct receptor_group_id) AS receptor_count"]
    tcr_dict["from"] = ["tcr AS s"]
    bcr_dict = deepcopy(tcr_dict)
    bcr_dict["from"] = ["bcr AS s"]

    # Cache the counts
    search_string = build_query(search_dict)
    tcr_string = build_query(tcr_dict)
    bcr_string = build_query(bcr_dict)
    query_strings = "\n".join([search_string, tcr_string, bcr_string])
    print(query_strings)
    if query_strings in counts:
        return deepcopy(counts[query_strings])

    cur.execute(search_string)
    row = cur.fetchone()
    result["epitope"]["count"] = row["epitope_count"]
    result["antigen"]["count"] = row["antigen_count"]
    result["assay"]["count"] = row["tcell_count"] + row["bcell_count"] + row["elution_count"]
    result["assay"]["tcell_count"] = row["tcell_count"]
    result["assay"]["bcell_count"] = row["bcell_count"]
    result["assay"]["elution_count"] = row["elution_count"]
    result["reference"]["count"] = row["reference_count"]

    cur.execute(tcr_string)
    row = cur.fetchone()
    result["receptor"]["tcr_count"] = row["receptor_count"]

    cur.execute(bcr_string)
    row = cur.fetchone()
    result["receptor"]["bcr_count"] = row["receptor_count"]

    result["receptor"]["count"] = result["receptor"]["tcr_count"] + result["receptor"]["bcr_count"]

    counts[query_strings] = deepcopy(result)
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
        result += "\nWHERE " + "\n  AND ".join(q["where"])
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
        html = ["div"]
        nav = ["ul", {"class": "nav nav-tabs justify-content-center", "style": "margin-bottom: 1em"}]
        nav.append(["li", {"class": "nav-item"}, ["a", {"class": "nav-link", "href": "/"}, "Home"]])
        tab = request.args.get("tab", "search")
        page = int(request.args.get("page", "1"))
        args = request.args.copy()
        args["page"] = 1
        if "tab2" in args:
            del args["tab2"]
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
            content = ["li", ["a", {"href": href(args, nonpeptide=nonpeptide)}, ["strong", current["label"]]]]
            if children and len(children) > 1:
                content.append(children)
            content = ["ul", content]
            tree = build_tree(tree, root, args, content)
            tree.insert(1, {"id": "hierarchy", "class": "col-md"})

            selected_nonpeptide_id = args.get("nonpeptide","")
            selected_nonpeptide_label = ""
            if selected_nonpeptide_id:
                selected_nonpeptide_label = current["label"]
            form = ["form",
                    {"id": "search-form", "class": "col"},
                    ["p",
                     ["a", {"class": "btn btn-primary", "href": "/search/?positive_assays_only=true"}, "Clear"],
                     ["input", {"class": "btn btn-success", "type": "submit", "value": "Search"}]],
                    ["p", {"class": "form-group form-check"},
                     ["input",
                      {"type": "checkbox",
                       "class": "form-check-input",
                       "name": "positive_assays_only",
                       "id": "positive_assays_only",
                       "value": "true",
                       "checked": request.args.get("positive_assays_only", "")}],
                     ["label", {"for": "positive_assays_only"}, "Positive assays only"]],
                    ["p", "structure type list"],
                    ["div",
                     {"id": "nonpeptides",
                      "class": "form-group row"},
                     ["label", {"for": "sequence", "class": "col-sm-3 col-form-label"}, "Epitope linear sequence"],
                     ["div",
                      {"class": "col-sm-9"},
                      ["input",
                       {"id": "sequence",
                        "class": "form-control",
                        "name": "sequence",
                        "type": "text",
                        "placeholder": "SIINFEKL",
                        "value": request.args.get("sequence", "")}]]],
                    ["div",
                     {"id": "nonpeptides",
                      "class": "form-group row"},
                     ["label", {"for": "nonpeptide", "class": "col-sm-3 col-form-label"}, "Non-Peptidic Epitope"],
                     ["div",
                      {"class": "col-sm-9"},
                      ["input",
                       {"id": "nonpeptide",
                        "name": "nonpeptide",
                        "type": "hidden",
                        "value": selected_nonpeptide_id}],
                      ["input",
                       {"class": "typeahead form-control",
                        "type": "text",
                        #"placeholder": "alcohol",
                        "value": selected_nonpeptide_label}]]],
                    ["p", "organism finder"],
                    ["p", "antigen finder"],
                    ["p", "mhc finder"],
                    ["p", "host finder"],
                    ["p", "disease finder"],
                    ["p", "qualitative measure"]]

            html.append(["div",
                         {"class": "row"},
                         form,
                         tree])

        elif tab == "epitope":
            q["select"] = [
                "structure_id",
                "description",
                "source_antigen_label",
                "source_organism_label",
                "count(distinct reference_id) AS \"references\"",
                "count(distinct assay_id) AS assays",
            ]
            q["group by"] = ["structure_id"]
            q["order by"] = ["\"references\" DESC"]

        elif tab == "antigen":
            q["select"] = [
                "source_antigen_label",
                "source_antigen_source_organism_label",
                "count(distinct structure_id) AS epitopes",
                "count(distinct assay_id) AS assays",
                "count(distinct reference_id) AS \"references\"",
            ]
            q["where"].append("source_antigen_id IS NOT NULL")
            q["group by"] = ["source_antigen_id"]
            q["order by"] = ["\"references\" DESC"]

        elif tab == "assay":
            nav = ["ul", {"class": "nav nav-tabs justify-content-center", "style": "margin-bottom: 1em"}]
            tab2 = request.args.get("tab2", "tcell")
            for table, title in [("tcell", "T Cell Assays"), ("bcell", "B Cell Assays"), ("elution", "MHC Ligand Assays")]:
                cls = "nav-link"
                if tab2 == table:
                    cls += " active"
                args["tab2"] = table
                args["page"] = 1
                count = result["assay"][f"{table}_count"]
                title += f" ({count})"
                nav.append(
                   ["li",
                    {"class": "nav-item"}, 
                    ["a",
                     {"class": cls, "href": "?" + urlencode(args)},
                     title]])
            html.append(nav)

            table = tab2
            count = result["assay"][f"{table}_count"]
            q["select"] = [f"DISTINCT {table}_id"]
            q["where"].append(f"{table}_id IS NOT NULL")
            query(cur, q)
            rows = cur.fetchall()
            ids = [str(row[f"{table}_id"]) for row in rows]
            ids = ", ".join(ids)
            q = {
              "select": ["*"],
              "from": [table],
              "where": [f"{table}_id IN ({ids})"]
            }

        elif tab == "receptor":
            nav = ["ul", {"class": "nav nav-tabs justify-content-center", "style": "margin-bottom: 1em"}]
            tab2 = request.args.get("tab2", "tcr")
            for table, title in [("tcr", "T Cell Receptors"), ("bcr", "B Cell Receptors")]:
                cls = "nav-link"
                if tab2 == table:
                    cls += " active"
                args["tab2"] = table
                args["page"] = 1
                count = result["receptor"][f"{table}_count"]
                title += f" ({count})"
                nav.append(
                   ["li",
                    {"class": "nav-item"},
                    ["a",
                     {"class": cls, "href": "?" + urlencode(args)},
                     title]])
            html.append(nav)

            table = tab2
            count = result["receptor"][f"{table}_count"]
            q["select"] = [
                "DISTINCT receptor_group_id AS receptor_id",
                "receptor_species_names",
                "receptor_type",
                "chain1_cdr3_sequence",
                "chain2_cdr3_sequence",
            ]
            q["from"] = [f"{table} AS s"]
            q["group by"] = ["receptor_group_id"]
            q["order by"] = ["receptor_group_id ASC"]

        elif tab == "reference":
            q["select"] = [
                "DISTINCT reference_id",
                "pubmed_id",
                "reference_author",
                "reference_title",
                "reference_date"
            ]
            q["order by"] = ["reference_date DESC"]

        if tab != "search":
            query(cur, q)
            html.append(make_paged_table(cur.fetchall(), count, dict(request.args)))

        return render_template("base.jinja2", html=tsv2rdf.render(html))


@app.route('/names.json')
def names():
    with sqlite3.connect(sqlite, uri=True) as conn:
        conn.row_factory = dict_factory
        cur = conn.cursor()
        text = request.args.get("text")
        if text:
            cur.execute(f"""
SELECT DISTINCT *
FROM names
WHERE name LIKE '%{text}%'
ORDER BY length(name)
LIMIT 100""")
        else:
            cur.execute(f"""SELECT DISTINCT * FROM names WHERE name IN ('cardiolipin', 'alcohol', 'nickel atom')""")
        return jsonify(cur.fetchall())


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
