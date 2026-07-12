# Relatório de Validação dos Dados para spaCy CRF

## Análise Visual do Corpus Gerado

Após a execução do pipeline de dados (data/offline_pipeline_crf.py), uma amostra visual do arquivo corpus_fasttext_crf.txt foi analisada. O conteúdo gerado é composto por nomes de logradouros (ex: "AVENIDA BRASIL", "RUA COSTA E SILVA") intercalados com seus respectivos bairros (ex: "TUCANO", "CHACARA"). Os dados apresentaram qualidade razoável, com as strings limpas e separadas por quebras de linha de forma consistente. Não foram observados sinais de "envenenamento" de dados, como caracteres indesejados, erros de encoding graves ou artefatos que poderiam prejudicar o treinamento do FastText ou do CRF, garantindo que o dataset está apto para os experimentos subsequentes.
