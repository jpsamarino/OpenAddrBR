# Relatório de Validação dos Dados para spaCy CRF

## Análise Visual do Corpus Gerado

Após a execução do pipeline de dados (data/offline_pipeline_crf.py), uma amostra visual do arquivo corpus_fasttext_crf.txt foi analisada. O conteúdo gerado é composto por nomes de logradouros (ex: "AVENIDA BRASIL", "RUA COSTA E SILVA") intercalados com seus respectivos bairros (ex: "TUCANO", "CHACARA"). Os dados apresentaram qualidade razoável, com as strings limpas e separadas por quebras de linha de forma consistente. Não foram observados sinais de "envenenamento" de dados, como caracteres indesejados, erros de encoding graves ou artefatos que poderiam prejudicar o treinamento do FastText ou do CRF, garantindo que o dataset está apto para os experimentos subsequentes.

## Treinamento FastText e spaCy CRF

Os embeddings treinados com o FastText (50 dimensões, window 3, min_count 1, 5 épocas) apresentaram um agrupamento semântico satisfatório para os tokens de logradouros, capturando similaridades em termos frequentes (como diferentes variações de "RUA" ou "AV").
Em relação às hiper-escolhas do modelo:
- **FastText**: 5 épocas provaram ser adequadas para o tamanho do corpus, permitindo boa convergência sem overfitting precoce.
- **spaCy CRF (NER)**: O otimizador foca na eficiência, com hiperparâmetros padrões adequados. Foi utilizada a inicialização de vetores pré-treinados estáticos gerados pelo FastText, com `dropout` configurado para 0.1, garantindo regularização contra overfitting em logradouros menos frequentes. (Nota de execução: em determinados ambientes Windows, o limite do MAX_PATH requer configurações específicas para o carregamento correto da biblioteca spaCy).

