#!/usr/bin/env python3

import argparse
import csv

from rdflib import Graph, URIRef, BNode, Literal

def iri2curie(prefixes, iri):
    for prefix, base in prefixes:
        if iri.startswith(base):
            return iri.replace(base, prefix + ":")
    raise Exception(f"No matching prefix for {iri}")


def rdf2tsv(prefixes_path, input_path, output_path):
    prefixes = []
    with open(prefixes_path) as f:
        rows = csv.reader(f, delimiter="\t")
        for row in rows:
            prefixes.append(row)
    prefixes.sort(key=lambda x: len(x[1]), reverse=True)
    
    headers = ["zn", "sc", "sb", "pc", "oi", "oc", "ob", "ol", "dc", "lt"]
    stanzas = {}
    later = []
    with open(output_path, "w") as f:
        writer = csv.DictWriter(f, headers, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        g = Graph()
        g.parse(input_path)
        for s, p, o in g:
            row = {}
            if isinstance(s, URIRef):
                row["sc"] = iri2curie(prefixes, s)
            elif isinstance(s, BNode):
                row["sb"] = "_:" + str(s)
            else:
                raise Exception(f"Bad subject {s}")

            if isinstance(p, URIRef):
                row["pc"] = iri2curie(prefixes, p)
            else:
                raise Exception(f"Bad predicate {p}")

            if isinstance(o, URIRef):
                try:
                    row["oc"] = iri2curie(prefixes, o)
                except:
                    row["oi"] = str(o)
            elif isinstance(o, BNode):
                row["ob"] = "_:" + str(o)
            elif isinstance(o, Literal):
                row["ol"] = o.value
                if o.datatype:
                    row["dc"] = iri2curie(prefixes, o.datatype)
                elif o.language:
                    row["lt"] = o.language
            else:
                raise Exception(f"Bad object {o}")

            if "sc" in row:
                row["zn"] = row["sc"]
                writer.writerow(row)
            else:
                if row["pc"] == "owl:annotatedSource":
                    if "oc" in row:
                        stanzas[row["sb"]] = row["oc"]
                    elif "ob" in row:
                        stanzas[row["sb"]] = row["ob"]
                later.append(row)

        # TODO: Handle depth
        for row in later:
            if row["sb"] in stanzas:
                row["zn"] = stanzas[row["sb"]]
            else:
                row["zn"] = row["sb"]
            writer.writerow(row)


def test_rdf2tsv():
    pass


def main():
    parser = argparse.ArgumentParser(description="Convert an RDF file to TSV")
    parser.add_argument("prefixes", type=str, help="The prefixes TSV file")
    parser.add_argument("input", type=str, help="The input RDF file")
    parser.add_argument("output", type=str, help="The output TSV file")
    args = parser.parse_args()

    rdf2tsv(args.prefixes, args.input, args.output)


if __name__ == "__main__":
    main()
