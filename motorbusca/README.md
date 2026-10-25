# Motor de busca de profissões de TI

Motor de busca (BM25) sobre 23 profissões de TI da base O*NET, com interface em Streamlit
e busca em português por meio de um glossário de termos de TI.

## Arquivos

- `app.py`: interface web
- `motor_busca.py`: índice invertido e ranking BM25
- `traducao_consulta.py`: tradução da consulta (glossário português → inglês)
- `titulos_pt.py`: títulos das profissões em português
- `stemmer.py`: stemmer de Porter (desligado por padrão em `motor_busca.py`)
- `db_config.py`: conexão com o MySQL, usada só se `dados_profissoes.json` não existir
- `dados_profissoes.json` e `traducoes.json`: dados das profissões e traduções

## Fonte dos dados

O*NET 30 Database, U.S. Department of Labor/Employment and Training Administration
(USDOL/ETA), licença CC BY 4.0.
