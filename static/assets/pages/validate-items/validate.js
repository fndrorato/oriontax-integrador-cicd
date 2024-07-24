function validateData(data, client_id, rowIndex, validar_type_product = true) {
    return new Promise(function(resolve, reject) {
        // Validações de cada campo
        var errors = [];

        var codeItem = data['id'];
        var clientId = client_id;
        var ncm = data['ncm'];
        var cest = data['cest'];
        var description = data['description'];
        var selectedCfop = data['cfop'];
        var selectedIcmsCst = data['icms_cst'];
        var selectedIcmsAliquota = data['icms_aliquota'];
        var selectedIcmsAliquotaReduzida = data['icms_aliquota_reduzida'];
        var selectedCbenef = data['cbenef']
        var selectedPisCofinsCst = data['piscofins_cst'];
        var selectedNaturezareceita = data['naturezareceita'];
        var tipoProduto = data['type_product'];

        // Trim description and check if it's empty after trimming
        description = description.trim();
        if (description === '') {
            errors.push({ field: 'description', message: "A descrição é obrigatória." });
        }

        if (validar_type_product) {
            if (tipoProduto === '' || tipoProduto === null || tipoProduto === undefined) {
                errors.push({ field: 'type_product', message: "O tipo de produto é obrigatório." });
            }
        }

        // Validação do NCM
        if (!/^\d{8}$/.test(ncm)) {
            errors.push({ field: 'ncm', message: 'NCM deve ter 8 dígitos.' });
        }

        // Validação do CEST
        if (cest && !/^\d{7}$/.test(cest)) {
            errors.push({ field: 'cest', message: 'CEST deve ter 7 dígitos.' });
        }

        // Validação de CFOP e ICMS CST
        if (selectedCfop == '5405' && selectedIcmsCst != '60') {
            errors.push({ field: 'icms_cst', message: 'Quando o CFOP é 5405, o ICMS CST deve ser 60.' });
        }

        // Revalidar condições
        if (selectedIcmsCst != '20' && selectedIcmsAliquota != selectedIcmsAliquotaReduzida) {
            errors.push({ field: 'icms_aliquota_reduzida', message: 'ICMS Alíquota Reduzida deve ser igual a ICMS Alíquota quando ICMS CST não for 20.' });
        }

        if (selectedIcmsCst == '40' || selectedIcmsCst == '41' || selectedIcmsCst == '60') {
            if (selectedIcmsAliquota != '0' || selectedIcmsAliquotaReduzida != '0') {
                errors.push({ field: 'icms_aliquota', message: 'Para ICMS ' + selectedIcmsCst + ', as alíquotas de ICMS precisam ser 0.' });
            }
        }

        if (selectedIcmsCst == '20') {
            if (icmsAliquotaData.hasOwnProperty(selectedIcmsAliquotaReduzida) && icmsAliquotaData[selectedIcmsAliquotaReduzida].dataCode != 1) {
                errors.push({ field: 'icms_aliquota_reduzida_code', message: 'O valor do ICMS alíquota reduzida não é válido.' });
            }
        }

        if (selectedIcmsCst == '40' || selectedIcmsCst == '41' || selectedIcmsCst == '20') {
            if (selectedCbenef) {
                if (cbenefData.hasOwnProperty(selectedCbenef) && cbenefData[selectedCbenef].icmsCst != selectedIcmsCst) {
                    errors.push({ field: 'cbenef_cst', message: 'Esta não é uma combinação válida do CBENEF com o ICMS/CST selecionado.' });
                }                    
            } else {
                errors.push({ field: 'cbenef_cst', message: 'Para o CST ICMS selecionado, o CBENEF é obrigatório.' });                
            }
        }        

        if (selectedPisCofinsCst == '04' || selectedPisCofinsCst == '05' || selectedPisCofinsCst == '06'){
            if (selectedNaturezareceita === '' || selectedNaturezareceita === null || selectedNaturezareceita === undefined) {
                errors.push({ field: 'naturezareceita', message: "Para o PIS/COFINS selecionado, a  Natureza Receita é obrigatória." });
            } else {
                var nr_id = findIdByCodeAndPiscofinsCst(naturezareceitaData, selectedNaturezareceita, selectedPisCofinsCst);
                if (nr_id === null) {
                    errors.push({ field: 'naturezareceita_cst', message: 'A combinação Natureza Receita: ' + selectedNaturezareceita + ' com o PIS/COFINS ' + selectedPisCofinsCst + ' não é uma combinação válida!' });
                } 
            }          
        } else {
            if (selectedNaturezareceita) {
                errors.push({ field: 'naturezareceita', message: "Para o PIS/COFINS selecionado, a  Natureza Receita não deve ser preenchida." });                
            }
        }

        // Se houver erros, rejeita a promessa com as mensagens de erro
        if (errors.length > 0) {
            resolve({ isValid: false, errors: errors });
        } else {
            resolve({ isValid: true });
        }
    });
}

function getAliquotas(code) {
    if (piscofinsData.hasOwnProperty(code)) {
        return piscofinsData[code];
    } else {
        return null; // ou qualquer outro valor padrão
    }
}  

function validateCode(code, client) {
    return new Promise(function(resolve, reject) {
        $.ajax({
            url: urlValidateCode,
            data: {
                'code': code,
                'client': client
            },
            dataType: 'json',
            success: function(data) {
                if (data.success === false) {
                    resolve(false);
                } else {
                    resolve(true);
                }
            },
            error: function() {
                reject('Erro ao validar o código. Tente novamente.');
            }
        });
    });
}   

function validateCodes(codes, client) {
    return new Promise(function(resolve, reject) {
        $.ajax({
            url: urlValidateCode, // Your server-side validation endpoint
            data: {
                'codes': JSON.stringify(codes), // Send codes as a JSON string
                'client': client
            },
            dataType: 'json',
            success: function(data) {
                if (data.success === false) {
                    // Handle error response from server (e.g., some codes invalid)
                    resolve(data.invalidCodes || []); // Resolve with an array of invalid codes
                } else {
                    resolve([]); // All codes are valid
                }
            },
            error: function() {
                reject('Erro ao validar os códigos. Tente novamente.');
            }
        });
    });
} 

function findIdByCodeAndPiscofinsCst(naturezareceitaData, code, piscofinsCst) {
    for (const entry of naturezareceitaData) {
        if (entry.code === code && entry.piscofinsCst === piscofinsCst) {
            return entry.id;
        }
    }
    return null; // Retorna null se não encontrar a combinação
}