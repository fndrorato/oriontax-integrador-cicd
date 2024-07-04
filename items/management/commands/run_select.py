import psycopg2
from psycopg2 import sql

def connect_and_query():
    try:
        # Conectar ao banco de dados
        connection = psycopg2.connect(
            user="tributario",
            password="tributario2023",
            host="abccacu.ddns.net",
            port="15432",
            database="tributario"
        )
        print("Conectado ao banco de dados PostgreSQL")

        try:
            # Criar um cursor
            cursor = connection.cursor()

            # Definir a consulta SQL
            query = sql.SQL("""
                SELECT cd_sequencial, cd_produto, tx_codigobarras, tx_descricaoproduto, tx_ncm, tx_cest, nr_cfop, nr_cst_icms, vl_aliquota_integral_icms,
                vl_aliquota_final_icms, vl_aliquota_fcp, tx_cbenef, nr_cst_pis, vl_aliquota_pis, nr_cst_cofins, vl_aliquota_cofins, nr_naturezareceita,
                tx_estadoorigem, tx_estadodestino 
                FROM tb_sysmointegradorenvio 
                ORDER BY cd_sequencial ASC
            """)

            # Executar a consulta
            cursor.execute(query)

            # Obter os resultados
            rows = cursor.fetchall()

            # Imprimir o número de linhas retornadas
            print(f"Número de linhas retornadas: {len(rows)}")

        except Exception as query_error:
            print(f"Erro ao executar a consulta: {query_error}")

        finally:
            # Fechar o cursor
            cursor.close()

    except Exception as connection_error:
        print(f"Erro ao conectar ao banco de dados: {connection_error}")

    finally:
        # Fechar a conexão
        if connection:
            connection.close()
            print("Conexão com o banco de dados fechada")

if __name__ == "__main__":
    connect_and_query()
