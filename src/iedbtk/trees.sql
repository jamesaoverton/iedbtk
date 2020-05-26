DROP TABLE IF EXISTS nonpeptide;
CREATE TABLE nonpeptide (
  parent TEXT,
  child TEXT
);

INSERT INTO nonpeptide VALUES
("CHEBI:33521", "CHEBI:28112"),
("CHEBI:33521", "CHEBI:27638");

SELECT * FROM nonpeptide;
