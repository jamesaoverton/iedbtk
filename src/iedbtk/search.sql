ATTACH DATABASE "file:build/source.db?mode=ro" AS source;


-- Make a search table
DROP TABLE IF EXISTS search;
CREATE TABLE search (
  search_id INTEGER PRIMARY KEY,
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
  tcell_id INT,
  bcell_id INT,
  elution_id INT,
  assay_id INT,
  assay_type_id TEXT,
  assay_positive BOOLEAN,
  reference_id INT,
  pubmed_id INT,
  reference_author TEXT,
  reference_title TEXT,
  reference_date INT
);

INSERT INTO search
SELECT simple_search_id AS search_id,
  structure_id,
  structure_description,
  NULLIF(source_antigen_obi_id, '') AS source_antigen_id,
  NULLIF(source_antigen_name, '') AS source_antigen_label,
  NULLIF(source_antigen_source_org_id, '')AS source_antigen_source_organism_id,
  NULLIF(source_antigen_source_org_name, '') AS source_antigen_source_organism_label,
  NULLIF(source_organism_id, ''),
  NULLIF(source_organism_name, '') AS source_organism_label,
  NULLIF(linear_sequence, ''),
  NULLIF(non_peptidic_obi_id, '') AS non_peptide_id,
  NULLIF(tcell_id, ''),
  NULLIF(bcell_id, ''),
  NULLIF(elution_id, ''),
  assay_id,
  as_type_id AS assay_type_id,
  like('Positive%', qualitative_measure) AS assay_positive,
  reference_id,
  NULLIF(pubmed_id, ''),
  NULLIF(reference_author, ''),
  NULLIF(reference_title, ''),
  NULLIF(reference_date, '')
FROM source.simple_search;

CREATE INDEX search_structure_id ON search(structure_id);
CREATE INDEX search_source_antigen_id ON search(source_antigen_id);
CREATE INDEX search_assay_id ON search(assay_id);
CREATE INDEX search_reference_id ON search(reference_id);
CREATE INDEX search_reference_date ON search(reference_date);
CREATE INDEX search_linear_sequence ON search(linear_sequence);
CREATE INDEX search_non_peptide_id ON search(non_peptide_id);
CREATE INDEX search_ids ON search(structure_id, source_antigen_id, assay_id, reference_id);




DROP TABLE IF EXISTS tcell;
CREATE TABLE tcell (
  tcell_id INT PRIMARY KEY,
  reference_id INT,
  reference_summary TXT,
  structure_id INT,
  epitope_description TXT,
  host_id TXT,
  host_label TXT,
  immunization_description TXT,
  antigen_description TXT,
  antigen_epitope_relation TXT,
  mhc_restriction TXT,
  assay_description TXT
);

INSERT INTO tcell
SELECT
  tcell_id,
  reference_id,
  reference_summary,
  structure_id,
  epitope_description,
  host_organism_id AS host_id,
  host AS host_label,
  immunization_description,
  antigen_description,
  antigen_er AS antigen_epitope_relation,
  mhc_restriction,
  assay_description
FROM source.tcell_list;

CREATE INDEX tcell_tcell_id ON tcell(tcell_id);



DROP TABLE IF EXISTS bcell;
CREATE TABLE bcell (
  bcell_id INT PRIMARY KEY,
  reference_id INT,
  reference_summary TXT,
  structure_id INT,
  epitope_description TXT,
  host_id TXT,
  host_label TXT,
  immunization_description TXT,
  antigen_description TXT,
  antigen_epitope_relation TXT,
  assay_description TXT
);

INSERT INTO bcell
SELECT
  bcell_id,
  reference_id,
  reference_summary,
  structure_id,
  epitope_description,
  host_organism_id AS host_id,
  host AS host_label,
  immunization_description,
  antigen_description,
  antigen_er AS antigen_epitope_relation,
  assay_description
FROM source.bcell_list;

CREATE INDEX bcell_bcell_id ON bcell(bcell_id);




DROP TABLE IF EXISTS elution;
CREATE TABLE elution (
  elution_id INT PRIMARY KEY,
  reference_id INT,
  reference_summary TXT,
  structure_id INT,
  epitope_description TXT,
  antigen_processing TXT,
  mhc_restriction TXT,
  assay_description TXT,
  quantitative_measure TXT
);

INSERT INTO elution
SELECT
  elution_id,
  reference_id,
  reference_summary,
  structure_id,
  epitope_description,
  merged_host_imm_desc AS antigen_processing,
  mhc_restriction,
  assay_description,
  quantitative_measure
FROM source.mhc_elution_list;

CREATE INDEX elution_elution_id ON elution(elution_id);




-- Make a tcr table
DROP TABLE IF EXISTS tcr;
CREATE TABLE tcr (
  receptor_id INT,
  receptor_group_id INT,
  receptor_type TEXT,
  receptor_species_names TXT,
  chain1_cdr3_sequence TXT,
  chain2_cdr3_sequence TXT,
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
  tcell_id INT,
  bcell_id INT,
  elution_id INT,
  assay_id INT,
  assay_type_id TEXT,
  assay_positive BOOLEAN,
  reference_id INT,
  pubmed_id INT,
  reference_author TEXT,
  reference_title TEXT,
  reference_date INT
);

INSERT INTO tcr
SELECT RECEPTOR_ID AS receptor_id,
  RECEPTOR_GROUP_ID AS receptor_group_id,
  RECEPTOR_TYPE AS receptor_type,
  RECEPTOR_SPECIES_NAMES AS receptor_species_names,
  NULLIF(CHAIN1_CDR3_SEQ, '') AS chain1_cdr3_sequence,
  NULLIF(CHAIN2_CDR3_SEQ, '') AS chain2_cdr3_sequence,
  structure_id,
  structure_description,
  NULLIF(source_antigen_obi_id, '') AS source_antigen_id,
  NULLIF(source_antigen_name, '') AS source_antigen_label,
  NULLIF(source_antigen_source_org_id, '')AS source_antigen_source_organism_id,
  NULLIF(source_antigen_source_org_name, '') AS source_antigen_source_organism_label,
  NULLIF(source_organism_id, ''),
  NULLIF(source_organism_name, '') AS source_organism_label,
  NULLIF(linear_sequence, ''),
  NULLIF(non_peptidic_obi_id, '') AS non_peptide_id,
  NULLIF(tcell_id, ''),
  NULLIF(bcell_id, ''),
  NULLIF(elution_id, ''),
  assay_id,
  as_type_id AS assay_type_id,
  like('Positive%', qualitative_measure) AS assay_positive,
  reference_id,
  NULLIF(pubmed_id, ''),
  NULLIF(reference_author, ''),
  NULLIF(reference_title, ''),
  NULLIF(reference_date, '')
FROM source.tcell_receptor_list;

CREATE INDEX tcr_structure_id ON tcr(structure_id);
CREATE INDEX tcr_source_antigen_id ON tcr(source_antigen_id);
CREATE INDEX tcr_assay_id ON tcr(assay_id);
CREATE INDEX tcr_reference_id ON tcr(reference_id);
CREATE INDEX tcr_linear_sequence ON tcr(linear_sequence);
CREATE INDEX tcr_non_peptide_id ON tcr(non_peptide_id);
CREATE INDEX tcr_structure_assay_ids ON tcr(structure_id, assay_id);
CREATE INDEX tcr_structure_reference_ids ON tcr(structure_id, reference_id);
CREATE INDEX tcr_ids ON tcr(structure_id, source_antigen_id, assay_id, reference_id);




-- Make a bcr table
DROP TABLE IF EXISTS bcr;
CREATE TABLE bcr (
  receptor_id INT,
  receptor_group_id INT,
  receptor_type TEXT,
  receptor_species_names TXT,
  chain1_cdr3_sequence TXT,
  chain2_cdr3_sequence TXT,
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
  tcell_id INT,
  bcell_id INT,
  elution_id INT,
  assay_id INT,
  assay_type_id TEXT,
  assay_positive BOOLEAN,
  reference_id INT,
  pubmed_id INT,
  reference_author TEXT,
  reference_title TEXT,
  reference_date INT
);

INSERT INTO bcr
SELECT RECEPTOR_ID AS receptor_id,
  RECEPTOR_GROUP_ID AS receptor_group_id,
  RECEPTOR_TYPE AS receptor_type,
  RECEPTOR_SPECIES_NAMES AS receptor_species_names,
  NULLIF(CHAIN1_CDR3_SEQ, '') AS chain1_cdr3_sequence,
  NULLIF(CHAIN2_CDR3_SEQ, '') AS chain2_cdr3_sequence,
  structure_id,
  structure_description,
  NULLIF(source_antigen_obi_id, '') AS source_antigen_id,
  NULLIF(source_antigen_name, '') AS source_antigen_label,
  NULLIF(source_antigen_source_org_id, '')AS source_antigen_source_organism_id,
  NULLIF(source_antigen_source_org_name, '') AS source_antigen_source_organism_label,
  NULLIF(source_organism_id, ''),
  NULLIF(source_organism_name, '') AS source_organism_label,
  NULLIF(linear_sequence, ''),
  NULLIF(non_peptidic_obi_id, '') AS non_peptide_id,
  NULLIF(tcell_id, ''),
  NULLIF(bcell_id, ''),
  NULLIF(elution_id, ''),
  assay_id,
  as_type_id AS assay_type_id,
  like('Positive%', qualitative_measure) AS assay_positive,
  reference_id,
  NULLIF(pubmed_id, ''),
  NULLIF(reference_author, ''),
  NULLIF(reference_title, ''),
  NULLIF(reference_date, '')
FROM source.bcell_receptor_list;

CREATE INDEX bcr_structure_id ON bcr(structure_id);
CREATE INDEX bcr_source_antigen_id ON bcr(source_antigen_id);
CREATE INDEX bcr_assay_id ON bcr(assay_id);
CREATE INDEX bcr_reference_id ON bcr(reference_id);
CREATE INDEX bcr_linear_sequence ON bcr(linear_sequence);
CREATE INDEX bcr_non_peptide_id ON bcr(non_peptide_id);
CREATE INDEX bcr_structure_assay_ids ON bcr(structure_id, assay_id);
CREATE INDEX bcr_structure_reference_ids ON bcr(structure_id, reference_id);
CREATE INDEX bcr_ids ON bcr(structure_id, source_antigen_id, assay_id, reference_id);
