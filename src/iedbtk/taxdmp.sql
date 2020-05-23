DROP TABLE IF EXISTS nodes;
CREATE TABLE nodes (
  tax_id int,                         -- node id in GenBank taxonomy database
  parent_tax_id int,                  -- parent node id in GenBank taxonomy database
  rank text,                          -- rank of this node (superkingdom, kingdom, ...)
  embl_code text,                     -- locus-name prefix; not unique
  division_id int,                    -- see division.dmp file
  inherited_div_flag int,             -- 1 if node inherits division from parent
  genetic_code_id int,                -- see gencode.dmp file
  inherited_GC_flag int,              -- 1 if node inherits genetic code from parent
  mitochondrial_genetic_code_id int,  -- see gencode.dmp file
  inherited_MGC_flag int,             -- 1 if node inherits mitochondrial gencode from parent
  GenBank_hidden_flag int,            -- 1 if name is suppressed in GenBank entry lineage
  hidden_subtree_root_flag int,       -- 1 if this subtree has no sequence data yet
  comments text                       -- free-text comments and citations
);

DROP TABLE IF EXISTS names;
CREATE TABLE names (
  tax_id int,        -- the id of node associated with this name
  name_txt text,     -- name itself
  unique_name text,  -- the unique variant of this name if name not unique
  name_class text    -- (synonym, common name, ...)
);

DROP TABLE IF EXISTS citations;
CREATE TABLE citations (
 cit_id int,      -- the unique id of citation
 cit_key text,    -- citation key
 pubmed_id id,    -- unique id in PubMed database (0 if not in PubMed)
 medline_id id,   -- unique id in MedLine database (0 if not in MedLine)
 url text,        -- URL associated with citation
 text text,       -- any text (usually article name and authors).
                  -- The following characters are escaped in this text by a backslash:
                  -- newline (appear as "\n"),
                  -- tab character ("\t"),
                  -- double quotes ('\"'),
                  -- backslash character ("\\").
 taxid_list text  -- list of node ids separated by a single space
);

DROP TABLE IF EXISTS merged;
CREATE TABLE merged (
  old_tax_id int,  -- id of nodes which has been merged
  new_tax_id int   -- id of nodes which is result of merging
);

DROP TABLE IF EXISTS delnodes;
CREATE TABLE delnodes (
  tax_id int  -- deleted node id
);

DROP INDEX IF EXISTS nodes_tax_id;
DROP INDEX IF EXISTS names_tax_id;

.mode tabs
.import build/taxdmp/nodes.tsv nodes
.import build/taxdmp/names.tsv names
.import build/taxdmp/merged.tsv merged
.import build/taxdmp/delnodes.tsv delnodes
.import build/taxdmp/citations.tsv citations

CREATE INDEX nodes_tax_id ON nodes(tax_id);
CREATE INDEX names_tax_id ON names(tax_id);

-- Check work
--.tables
--select * from nodes limit 3;
--select * from merged limit 3;
--select * from delnodes limit 3;
--select * from names limit 3;
--select * from citations limit 3;
