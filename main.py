import yfinance as yf
import pandas as pd
import json
import psycopg2 as pg
import os
import logging
import requests
from psycopg2 import OperationalError   
from contextlib import closing
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Banco:
    def __init__(self):
        load_dotenv('vault.env')
        requered_env = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing_env = [env for env in requered_env if env not in os.environ]
        if missing_env:
            raise ValueError(f'Variáveis de ambiente faltantes: {", ".join(missing_env)}')
        self.db_host = os.getenv('DB_HOST')
        self.port = os.getenv('DB_PORT')            
        self.database = os.getenv('DB_NAME')            
        self.user = os.getenv('DB_USER')            
        self.db_key = os.getenv('DB_PASSWORD')  
    def conexao(self):
        try:
            connection = pg.connect(
                database=self.database,
                user=self.user,
                password=self.db_key,
                host=self.db_host,
                port=self.port
            )
            logging.info('Conexão efetuada!')
            return connection
        except OperationalError as e:
            logging.error(f'Erro ao conectar ao banco de dados: {e}')
            raise e
    def create_table(self):
        with closing(self.conexao()) as conection:
            with conection.cursor() as cursor:
                cursor.execute("""                            
                    CREATE TABLE IF NOT EXISTS raw_acoes (
                        ticker VARCHAR(10) NOT NULL UNIQUE,
                        data JSONB,
                        ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                """)        
                conection.commit()
    def insert_data(self,connection:pg,ticker:str,data_json:str):
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO raw_acoes (ticker, data, ingested_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (ticker)
                DO UPDATE SET
                    data = EXCLUDED.data,
                    ingested_at = CURRENT_TIMESTAMP
            """, (ticker, data_json))
            connection.commit()
            logging.info(f'Ticker {ticker} salvo/atualizado com sucesso no lote.')

class Data:
    def __init__(self, banco, request):
        self.request = request
        self.banco = banco
    
    def save_data(self):
        try:
            with closing(self.banco.conexao()) as connection:
                for ticker in self.request.config['ticker']:
                    data_request = self.request.request_data(ticker)
                    if data_request:
                        self.banco.insert_data(connection, ticker, data_request)
                logging.info("Todos os dados foram salvos com sucesso no lote.")
        except Exception as e:
            logging.error(f'Erro ao salvar os dados: {e}')

class Request:
    def __init__(self):
        self.config = json.load(open('config.json'))
    def request_data(self, ticker:str):
            try:
                df = yf.download(ticker, period=self.config['period'], interval=self.config['interval'], progress=False)
                df_rest = df.reset_index()
                df_json = df_rest.to_json(orient='records', date_format='iso')
                return df_json
            except requests.exceptions.RequestException as e:
                logging.error(f'Erro de rede para o ticker {ticker}: {e}')
                return None
            except (KeyError, ValueError) as e:
                logging.error(f'Erro ao baixar dados do ticker {ticker}: {e}')
                return None
            except Exception as e:
                logging.error(f'Erro inesperado na requisição: {e}')
                return None


if __name__ == '__main__':
    banco = Banco()
    request = Request()
    data = Data(banco, request)
    banco.create_table()
    data.save_data()    