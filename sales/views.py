import psycopg2
from psycopg2 import sql
from config import load_config

def connect(config):
    """ Connect to the PostgreSQL database server """
    try:
        # connecting to the PostgreSQL server
        with psycopg2.connect(**config) as conn:
            print('Connected to the PostgreSQL server.')
            # Execute a test query
            test_query(conn)
    except (Exception. psycopg2.DatabaseError ) as error:
        print(error)


def test_query(connection):
    """ Test a query and print the number of rows found """
    print('Test a query and print the number of rows found')
    try:
        with connection.cursor() as cursor:
            print('Dentro do With Connection')
            query = sql.SQL("""
                SELECT cd_sequencial, cd_produto, tx_codigobarras, tx_descricaoproduto, tx_ncm, tx_cest, nr_cfop, nr_cst_icms, vl_aliquota_integral_icms,
                    vl_aliquota_final_icms, vl_aliquota_fcp, tx_cbenef, nr_cst_pis, vl_aliquota_pis, nr_cst_cofins, vl_aliquota_cofins, nr_naturezareceita,
                    tx_estadoorigem, tx_estadodestino 
                FROM tb_sysmointegradorenvio
                ORDER BY cd_sequencial ASC
                LIMIT 53600
            """)
            print('Passou pelo query')
            cursor.execute(query)
            print('Passou pelo execute')
            batch_size = 1000  # Defina um tamanho de lote apropriado
            total_rows = 0

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                total_rows += len(rows)
                # Processar os dados aqui, se necessário
                print(f"Processed {len(rows)} rows")

            print(f"Total rows processed: {total_rows}")

    except Exception as error:
        print(f"Error executing the query: {error}")

if __name__ == '__main__':
    config = load_config()
    connect(config)
