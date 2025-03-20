from django.db import models
from clients.models import Client
from items.models import Item

class SalesCab(models.Model):
    CNPJ = models.CharField(max_length=14)  # CNPJ do emitente
    client = models.ForeignKey(Client, on_delete=models.RESTRICT, blank=True, null=True)
    xNome = models.CharField(max_length=200)  # Razão social ou nome do emitente
    xFant = models.CharField(max_length=200, blank=True, null=True)  # Nome fantasia    
    nNF = models.CharField(max_length=20)  # Número da nota fiscal
    serie = models.CharField(max_length=10)  # Série da NF
    tpNF = models.IntegerField()  # Tipo de operação da NF
    cUF = models.IntegerField()  # Código da UF do emitente
    cNF = models.CharField(max_length=10)  # Código numérico que compõe a chave de acesso
    natOp = models.CharField(max_length=100)  # Natureza da operação
    mod = models.CharField(max_length=10)  # Modelo do documento fiscal
    cMunFG = models.IntegerField(default=0, blank=True, null=True)  # Código do município de ocorrência do fato gerador
    tpAmb = models.IntegerField()  # Tipo de ambiente (produção ou homologação)
    dhEmi = models.DateTimeField()  # Data e hora de emissão
    IE = models.CharField(max_length=20, blank=True, null=True)  # Inscrição Estadual
    CRT = models.IntegerField()  # Código de Regime Tributário
    cMun = models.IntegerField(default=0, blank=True, null=True)  # Código do município do emitente
    xMun = models.CharField(max_length=100)  # Nome do município do emitente
    UF = models.CharField(max_length=2, blank=True, null=True)  # UF do emitente
    user = models.IntegerField(default=0, blank=True, null=True) # id do usuario que exportou
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('CNPJ', 'nNF', 'serie', 'tpNF'),)  # Define a chave composta como chave primária

    def __str__(self):
        return f"NF: {self.nNF}, Série: {self.serie}, Tipo: {self.tpNF}"

class SalesDet(models.Model):
    sales_cab = models.ForeignKey(SalesCab, on_delete=models.CASCADE, related_name="details")
    prod_NumItem = models.IntegerField()  # Número do item no detalhe
    item = models.ForeignKey(Item, on_delete=models.CASCADE, blank=True, null=True)
    cProd = models.CharField(max_length=50)  # Código do produto
    cEAN = models.CharField(max_length=20, blank=True, null=True)  # Código EAN
    xProd = models.CharField(max_length=200)  # Descrição do produto
    NCM = models.CharField(max_length=8)  # Código NCM
    CEST = models.CharField(max_length=17, blank=True, null=True)  # Código CEST
    CFOP = models.CharField(max_length=4)  # Código CFOP
    uCom = models.CharField(max_length=6)  # Unidade de comercialização
    qCom = models.DecimalField(max_digits=15, decimal_places=4)  # Quantidade comercializada
    vUnCom = models.DecimalField(max_digits=15, decimal_places=4)  # Valor unitário de comercialização
    vProd = models.DecimalField(max_digits=15, decimal_places=2)  # Valor total do produto
    cEANTrib = models.CharField(max_length=13, blank=True, null=True)  # Código EAN de tributação
    uTrib = models.CharField(max_length=6)  # Unidade de tributação
    qTrib = models.DecimalField(max_digits=15, decimal_places=4)  # Quantidade tributável
    vUnTrib = models.DecimalField(max_digits=15, decimal_places=4)  # Valor unitário de tributação
    indTot = models.IntegerField()  # Indicador de totalização
    ICMS_orig = models.IntegerField()  # Origem do ICMS
    ICMS_CST = models.IntegerField()  # Código CST do ICMS
    ICMS_modBC = models.IntegerField(blank=True, null=True)  # Modalidade de determinação da BC do ICMS
    ICMS_vBC = models.DecimalField(max_digits=15, decimal_places=2)  # Valor da BC do ICMS
    ICMS_pICMS = models.DecimalField(max_digits=5, decimal_places=2)  # Alíquota do ICMS
    ICMS_vICMS = models.DecimalField(max_digits=15, decimal_places=2)  # Valor do ICMS
    PIS_CST = models.IntegerField()  # Código CST do PIS
    PIS_vBC = models.DecimalField(max_digits=15, decimal_places=2)  # Valor da BC do PIS
    PIS_pPIS = models.DecimalField(max_digits=5, decimal_places=2)  # Alíquota do PIS
    PIS_vPIS = models.DecimalField(max_digits=15, decimal_places=2)  # Valor do PIS
    PIS_PISAliq = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)  # Alíquota específica do PIS
    COFINS_CST = models.IntegerField()  # Código CST do COFINS
    COFINS_vBC = models.DecimalField(max_digits=15, decimal_places=2)  # Valor da BC do COFINS
    COFINS_pCOFINS = models.DecimalField(max_digits=5, decimal_places=2)  # Alíquota do COFINS
    COFINS_vCOFINS = models.DecimalField(max_digits=15, decimal_places=2)  # Valor do COFINS
    COFINS_COFINSAliq = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)  # Alíquota específica do COFINS
    prod_cBenef = models.CharField(max_length=20, blank=True, null=True)  # Código do benefício fiscal
    ICMS_pRedBC = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # Percentual de redução da BC do ICMS
    PIS_PISNT = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)  # PIS não tributável
    COFINS_COFINSNT = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)  # COFINS não tributável
    item_validado = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    validado_at = models.DateTimeField(null=True, blank=True)
    motivo_valicadao = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = (('sales_cab', 'prod_NumItem'),)  # Define a chave primária composta
    
    def __str__(self):
        return f"Item {self.prod_NumItem} do Produto: {self.cProd}, Quantidade: {self.qCom}, Valor: {self.vProd}"

class FileProcessingLog(models.Model):
    csv_file_name = models.CharField(max_length=255)
    log = models.TextField()
    resultado = models.BooleanField()
    data_hora_criado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.csv_file_name} - {self.data_hora_criado}"

class SalesPedido(models.Model):
    """Tabela SalesPedido (dados gerais da nota fiscal)."""
    arquivo_id = models.CharField(max_length=100)  # Chave identificadora do arquivo ZIP
    chNFe = models.CharField(max_length=50, unique=True)  # Chave da NF-e
    tpAmb = models.IntegerField()
    verAplic = models.CharField(max_length=20)
    dhRecbto = models.DateTimeField()
    nProt = models.CharField(max_length=50, blank=True, null=True)
    digVal = models.CharField(max_length=50, blank=True, null=True)
    cStat = models.IntegerField()
    xMotivo = models.CharField(max_length=255)
    cUF = models.IntegerField()
    cNF = models.IntegerField()
    natOp = models.CharField(max_length=255)
    mod = models.IntegerField()
    serie = models.IntegerField()
    nNF = models.IntegerField()
    dhEmi = models.DateTimeField()
    dhSaiEnt = models.DateTimeField(null=True, blank=True)
    tpNF = models.IntegerField()
    idDest = models.IntegerField()
    cMunFG = models.IntegerField()
    tpImp = models.IntegerField()
    tpEmis = models.IntegerField()
    cDV = models.IntegerField()
    finNFe = models.IntegerField()
    indFinal = models.IntegerField()
    indPres = models.IntegerField()
    procEmi = models.IntegerField()
    verProc = models.CharField(max_length=50)
    
    # Emitente
    CNPJ_Emitente = models.CharField(max_length=20)
    xNome_Emitente = models.CharField(max_length=255)
    xLgr_Emitente = models.CharField(max_length=255)
    nro_Emitente = models.CharField(max_length=20)
    xBairro_Emitente = models.CharField(max_length=100)
    cMun_Emitente = models.IntegerField()
    xMun_Emitente = models.CharField(max_length=100)
    UF_Emitente = models.CharField(max_length=2)
    CEP_Emitente = models.CharField(max_length=20)
    fone_Emitente = models.CharField(max_length=20, blank=True, null=True)
    IE_Emitente = models.CharField(max_length=50, blank=True, null=True)
    CRT_Emitente = models.IntegerField()

    # Destinatário
    CNPJ_Destinatario = models.CharField(max_length=20, blank=True, null=True)
    CPF_Destinatario = models.CharField(max_length=20, blank=True, null=True)
    xNome_Destinatario = models.CharField(max_length=255, blank=True, null=True)
    xLgr_Destinatario = models.CharField(max_length=255, blank=True, null=True)
    nro_Destinatario = models.CharField(max_length=20, blank=True, null=True)
    xBairro_Destinatario = models.CharField(max_length=100, blank=True, null=True)
    cMun_Destinatario = models.IntegerField(blank=True, null=True)
    xMun_Destinatario = models.CharField(max_length=100, blank=True, null=True)
    UF_Destinatario = models.CharField(max_length=2, blank=True, null=True)
    CEP_Destinatario = models.CharField(max_length=20, blank=True, null=True)
    fone_Destinatario = models.CharField(max_length=20, blank=True, null=True)
    indIEDestinatario = models.IntegerField(blank=True, null=True)
    IE_Destinatario = models.CharField(max_length=50, blank=True, null=True)

    # Valores da NF-e
    vBC = models.DecimalField(max_digits=10, decimal_places=2)
    vICMS = models.DecimalField(max_digits=10, decimal_places=2)
    vICMSDeson = models.DecimalField(max_digits=10, decimal_places=2)
    vFCP = models.DecimalField(max_digits=10, decimal_places=2)
    vBCST = models.DecimalField(max_digits=10, decimal_places=2)
    vST = models.DecimalField(max_digits=10, decimal_places=2)
    vFCPST = models.DecimalField(max_digits=10, decimal_places=2)
    vFCPSTRet = models.DecimalField(max_digits=10, decimal_places=2)
    vProd = models.DecimalField(max_digits=10, decimal_places=2)
    vFrete = models.DecimalField(max_digits=10, decimal_places=2)
    vSeg = models.DecimalField(max_digits=10, decimal_places=2)
    vDesc = models.DecimalField(max_digits=10, decimal_places=2)
    vII = models.DecimalField(max_digits=10, decimal_places=2)
    vIPI = models.DecimalField(max_digits=10, decimal_places=2)
    vIPIDevol = models.DecimalField(max_digits=10, decimal_places=2)
    vPIS = models.DecimalField(max_digits=10, decimal_places=2)
    vCOFINS = models.DecimalField(max_digits=10, decimal_places=2)
    vOutro = models.DecimalField(max_digits=10, decimal_places=2)
    vNF = models.DecimalField(max_digits=10, decimal_places=2)

class SalesDetalhe(models.Model):
    """Tabela SalesDetalhe (itens da NF-e)."""
    pedido = models.ForeignKey(SalesPedido, on_delete=models.CASCADE, related_name="itens")
    chNFe = models.CharField(max_length=50, blank=True, null=True)  # Chave da NF-e
    nItem = models.IntegerField()
    cProd = models.CharField(max_length=50)
    xProd = models.CharField(max_length=255)
    NCM = models.CharField(max_length=10)
    cBenef = models.CharField(max_length=20, blank=True, null=True)
    CEST = models.CharField(max_length=20, blank=True, null=True)
    CFOP = models.IntegerField()
    uCom = models.CharField(max_length=10)
    qCom = models.DecimalField(max_digits=10, decimal_places=4)
    vUnCom = models.DecimalField(max_digits=10, decimal_places=4)
    vProd = models.DecimalField(max_digits=10, decimal_places=2)
    cEAN = models.CharField(max_length=20, blank=True, null=True)
    uTrib = models.CharField(max_length=10)
    qTrib = models.DecimalField(max_digits=10, decimal_places=4)
    vUnTrib = models.DecimalField(max_digits=10, decimal_places=4)
    cEANTrib = models.CharField(max_length=20, blank=True, null=True)
    vFrete = models.DecimalField(max_digits=10, decimal_places=2)
    vSeg = models.DecimalField(max_digits=10, decimal_places=2)
    vDesc = models.DecimalField(max_digits=10, decimal_places=2)
    vOutro = models.DecimalField(max_digits=10, decimal_places=2)
    indTot = models.IntegerField()
    orig = models.IntegerField()
    CST_ICMS = models.CharField(max_length=10)
    modBC = models.IntegerField()
    vBC = models.DecimalField(max_digits=10, decimal_places=2)
    pICMS = models.DecimalField(max_digits=5, decimal_places=2)
    vICMS = models.DecimalField(max_digits=10, decimal_places=2)
    vICMSDeson = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)
    pRedBC = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    modBCST = models.IntegerField(blank=True, null=True)
    vBCST = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    pICMSST = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    vICMSST = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    vPIS = models.DecimalField(max_digits=10, decimal_places=2)
    CST_PIS = models.CharField(max_length=10)
    pPIS = models.DecimalField(max_digits=5, decimal_places=2)
    vBC_PIS = models.DecimalField(max_digits=10, decimal_places=2)
    vCOFINS = models.DecimalField(max_digits=10, decimal_places=2)
    CST_COFINS = models.CharField(max_length=10)
    pCOFINS = models.DecimalField(max_digits=5, decimal_places=2)
    vBC_COFINS = models.DecimalField(max_digits=10, decimal_places=2)
    
    motDesICMS = models.IntegerField(blank=True, null=True, default=0)
    vFCPST = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)
    pFCPST = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)
    vFCP = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)
    pFCP = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)
    vST = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)
    pST = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)
    vBCSTRet = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)
    
    