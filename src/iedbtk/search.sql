-- Make a search table
DROP TABLE IF EXISTS search;
CREATE TABLE search (
  search_id INTEGER PRIMARY KEY AUTOINCREMENT,
  structure_id INT,
  description TEXT,
  source_antigen_id TEXT,
  source_antigen_label TEXT,
  source_antigen_source_organism_id TEXT,
  source_antigen_source_organism_label TEXT,
  source_organism_id TEXT,
  source_organism_label TEXT,
  linear_sequence TEXT,
  non_peptide_id TEXT,
  non_peptide_label TEXT,
  tcell_id INT,
  bcell_id INT,
  elution_id INT,
  assay_id INT,
  assay_type_id TEXT,
  reference_id INT,
  pubmed_id INT,
  reference_author TEXT,
  reference_title TEXT,
  reference_date INT
);


ATTACH DATABASE "file:build/temp.db?mode=ro" AS source;


INSERT INTO search
SELECT NULL AS search_id,
  structure_id,
  structure_description,
  source_antigen_obi_id AS source_antigen_id,
  source_antigen_name AS source_antigen_label,
  source_antigen_source_org_id AS source_antigen_source_organism_id,
  source_antigen_source_org_name AS source_antigen_source_organism_label,
  source_organism_id,
  source_organism_name AS source_organism_label,
  linear_sequence,
  replace(non_peptidic_obi_id, 'http://purl.obolibrary.org/obo/CHEBI_', 'CHEBI:') AS non_peptide_id,
  non_peptidic_obi_id AS non_peptide_label,
  tcell_id,
  bcell_id,
  elution_id,
  assay_id,
  as_type_id AS assay_type_id,
  reference_id,
  pubmed_id,
  reference_author,
  reference_title,
  reference_date
FROM source.simple_search;

CREATE INDEX search_structure_id ON search(structure_id);
CREATE INDEX search_source_antigen_id ON search(source_antigen_id);
CREATE INDEX search_assay_id ON search(assay_id);
CREATE INDEX search_reference_id ON search(reference_id);
CREATE INDEX search_linear_sequence ON search(linear_sequence);
CREATE INDEX search_non_peptide_id ON search(non_peptide_id);
CREATE INDEX search_structure_assay_ids ON search(structure_id, assay_id);
CREATE INDEX search_structure_reference_ids ON search(structure_id, reference_id);
CREATE INDEX search_ids ON search(structure_id, source_antigen_id, assay_id, reference_id);
