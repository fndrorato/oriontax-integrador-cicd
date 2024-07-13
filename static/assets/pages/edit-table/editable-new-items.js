'use strict';
$(document).ready(function() {  

    $('#new-items-table').Tabledit({
        groupClass: 'btn-group btn-group-mini',
        deleteButton: false,
        url: null,
        columns: {
            identifier: [0, 'id'],
            editable: [
                [1, 'barcode'], 
                [2, 'description'], 
                [3, 'ncm'], 
                [4, 'cest']
            ]
        },
        buttons: {
            edit: {
                class: 'btn btn-mini btn-primary', 
                html: '<a class="icofont icofont-ui-edit"></a>',
                action: 'edit'
            },
            delete: {
                class: 'btn btn-sm btn-danger',
                html: '<span class="fa fa-trash"></span> Excluir',
                action: 'delete'
            },
            save: {
                class: 'btn btn-mini btn-success',
                html: '<span class="icofont icofont-ui-check"></span>',
                action: 'save'
            },
            restore: {
                class: 'btn btn-sm btn-warning',
                html: 'Restaurar',
                action: 'restore'
            },
            confirm: {
                class: 'btn btn-sm btn-default',
                html: 'Confirmar'
            }
        },
        onDraw: function() {
            // Callback para quando a tabela é desenhada
            // Add listener to edit buttons
            $('#new-items-table').find('.tabledit-edit-button').on('click', function() {
                // Get the current row
                var $row = $(this).closest('tr');
                
                // Get the values of the fields
                var id = $row.find('td').eq(0).text();
                var barcode = $row.find('td').eq(1).find('.tabledit-input').val() || $row.find('td').eq(1).text();
                var description = $row.find('td').eq(2).find('.tabledit-input').val() || $row.find('td').eq(2).text();
                var ncm = $row.find('td').eq(3).find('.tabledit-input').val() || $row.find('td').eq(3).text();
                var cest = $row.find('td').eq(4).find('.tabledit-input').val() || $row.find('td').eq(4).text();

            });            
        },
        onSuccess: function(data, textStatus, jqXHR) {
            // Callback para quando uma ação é bem-sucedida
            console.log("Updated row data:", data);
        },
        onFail: function(jqXHR, textStatus, errorThrown) {
            // Callback para quando uma ação falha
            console.log('onFail(jqXHR, textStatus, errorThrown)');
            console.log(jqXHR);
            console.log(textStatus);
            console.log(errorThrown);            
        },
        onAlways: function() {
            // Callback que sempre é chamado
        },
        onAjax: function(action, serialize) {
            var data = {};
            var $row = $('#new-items-table').find('tr.custom-edit-mode');
        
            if ($row.length > 0) {
                $row.find('input, select').each(function() {
                    var name = $(this).attr('name');
                    var value = $(this).val();
                    data[name] = value;
        
                    if ($(this).is('select')) {
                        var selectedOption = $(this).find('option:selected');
                        var dataCst = selectedOption.data('cst');
                        var dataCode = selectedOption.data('code');
                        if (dataCode !== undefined) {
                            data[name + '_code'] = dataCode;
                        }                         
                        if (dataCst !== undefined) {
                            data[name + '_cst'] = dataCst;
                        }                    
                    }                    
                });
        
                // Chamar validateData e capturar a Promessa resultante
                try {
                    var resultValidate = validateData(data);
                    $row.addClass('validation-error custom-edit-mode');
                    resultValidate.then(function(isValid) {
                        if (isValid) {
                            data['code'] = data['id'];
                            data['client'] = client_id;

                            var aliquotas = getAliquotas(data['piscofins_cst']);
                            data['pis_aliquota'] = aliquotas.pis_aliquota;
                            data['cofins_aliquota'] = aliquotas.cofins_aliquota; 
                            data['fix_item'] = 0;                           
            
                            serialize = '';
                            serialize += $.param(data);
            
                            // Enviar os dados para a URL especificada via AJAX
                            $.ajax({
                                url: urlNewItem,
                                type: 'POST',
                                data: serialize,
                                success: function(response) {
                                    // Validar o status da resposta
                                    if (response.status === 'success') {
                                        console.log('Data successfully sent to the server:', response.message);

                                        // Chamar a função notify
                                        notify('top', 'right', 'fa fa-check', 'success', 'animated bounceInRight', 'animated bounceOutRight', 'Resultado', 'Produto adicionado com sucesso!');

                                        // Adicionar a classe tr-success à linha correspondente
                                        $row.addClass('tr-success').removeClass('custom-edit-mode validation-error');

                                        // Remover o botão de editar da linha
                                        $row.find('.tabledit-edit-button').remove(); 
                                        $row.find('span.tx_type_product').text(data['type_product']);                                      
                                    } else {
                                        console.error('Error:', response.message);
                                        // Você pode optar por chamar uma notificação de erro aqui, se necessário
                                        notify('top', 'right', 'fa fa-times', 'danger', 'animated bounceInRight', 'animated bounceOutRight', 'Ops', 'Ocorreu um erro ao salvar o produto. Tente novamente.');
                                        $row.addClass('validation-error');
                                        return false;
                                    }
                                },
                                error: function(jqXHR, textStatus, errorThrown) {
                                    console.error('Error sending data to the server:', textStatus, errorThrown);
                                    $row.addClass('validation-error');
                                    return false;
                                }
                            });
                        } else {
                            console.error('Validation failed.');
                            $row.addClass('validation-error custom-edit-mode');
                            $row.find('.tabledit-edit-button').trigger('click');
                            return false;
                        }
                    }).catch(function(error) {
                        console.error('Validation error:', error);
                        $row.addClass('validation-error custom-edit-mode');
                        return false;
                    });                     
                      
                } catch (error) {
                    $row.addClass('validation-error custom-edit-mode');
                    console.error('Validation error:', error);
                    return false;
                    
                }
            } else {
                console.error('No row in edit mode found.');
                return false;
            }

            return true;
        }
    });  
    
    // Adicionar e remover a classe personalizada ao iniciar e finalizar a edição
    $('#new-items-table').on('click', '.tabledit-edit-button', function() {
        $(this).closest('tr').addClass('custom-edit-mode');
    });

    $('#new-items-table').on('click', '.tabledit-save-button, .tabledit-confirm-button', function() {
        var $row = $(this).closest('tr').removeClass('custom-edit-mode');

        // Ajustar o texto do span para o campo cbenef
        $row.find('select[name="cbenef"]').each(function() {
            var selectedText = $(this).find('option:selected').text();
            var displayText = selectedText.split('-')[0].trim();
            $(this).siblings('.tabledit-span').text(displayText);
        });

        $row.find('select[name="piscofins_cst"]').each(function() {
            var selectedText = $(this).find('option:selected').text();
            var displayText = selectedText.split('-')[0].trim();
            $(this).siblings('.tabledit-span').text(displayText);
        });
        
        $row.find('select[name="naturezareceita"]').each(function() {
            var selectedText = $(this).find('option:selected').text();
            var displayText = selectedText.split('-')[0].trim();
            $(this).siblings('.tabledit-span').text(displayText);
        });        
    }); 

    $('select[name="piscofins_cst"]').change(function() {
        // Obter o valor selecionado
        var selectedCode = $(this).val();
        // Buscar as aliquotas correspondentes
        var aliquotas = getAliquotas(selectedCode);
        if (aliquotas) {
            // Encontrar a linha atual
            var $row = $(this).closest('tr');
            // Atualizar os spans ou inputs na linha atual com os novos valores
            $row.find('span[name="pis_aliquota"]').text(aliquotas.pis_aliquota);
            $row.find('span[name="cofins_aliquota"]').text(aliquotas.cofins_aliquota);
        }
    });    
    
    function validateData(data) {
        return new Promise(function(resolve, reject) {
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
                alert("A descrição é obrigatória.");
                return resolve(false);
            }
    
            // Check if tipoProduto is selected
            if (tipoProduto === '' || tipoProduto === null || tipoProduto === undefined) {
                alert("O tipo de produto é obrigatório.");
                return resolve(false);
            }
    
            // Validação do NCM
            if (!/^\d{8}$/.test(ncm)) {
                alert('NCM deve ter 8 dígitos.');
                return resolve(false);
            }
    
            // Validação do CEST
            if (cest && !/^\d{7}$/.test(cest)) {
                alert('CEST deve ter 7 dígitos.');
                return resolve(false);
            }
    
            // Validação de CFOP e ICMS CST
            if (selectedCfop == '5405' && selectedIcmsCst != '60') {
                alert('Quando o CFOP é 5405, o ICMS CST deve ser 60.');
                return resolve(false);
            }
    
            // Revalidar condições
            if (selectedIcmsCst != '20' && selectedIcmsAliquota != selectedIcmsAliquotaReduzida) {
                alert('ICMS Alíquota Reduzida deve ser igual a ICMS Alíquota quando ICMS CST não for 20.');
                return resolve(false);
            }
    
            if (selectedIcmsCst == '40' || selectedIcmsCst == '60') {
                if (selectedIcmsAliquota != '0' || selectedIcmsAliquotaReduzida != '0') {
                    alert('Para ICMS:' + selectedIcmsCst +' as alíquotas de ICMS precisam ser 0');
                    return resolve(false);
                }
            }
    
            if (selectedIcmsCst == '20') {
                if (data['icms_aliquota_reduzida_code'] != '1') {
                    alert('O valor do ICMS alíquota reduzida não é válido.');
                    return resolve(false);
                }
            }

            if (selectedCbenef) {
                if (data['cbenef_cst'] != selectedIcmsCst) {
                    alert('Esta não é uma combinação válida do CBENEF com o ICMS/CST selecionado.')
                    return resolve(false);
                }
            }
    
            if (selectedNaturezareceita && data['naturezareceita_cst']) {
                if (data['naturezareceita_cst'] != selectedPisCofinsCst) {
                    alert('A combinação Natureza Receita:' + data['naturezareceita_code'] + ' com o PIS/COFINS ' + selectedPisCofinsCst +' não é uma combinação válida!');
                    return resolve(false);
                }
            }
    
            // Se todas as validações passarem, verificar o código
            validateCode(codeItem, clientId).then(function(isValid) {
                if (!isValid) {
                    alert('Código do produto já existe para esse cliente.');
                    return resolve(false);
                } else {
                    return resolve(true);
                }
            }).catch(function(error) {
                alert(error); // Tratar erros de validação do código
                return resolve(false);

            });
        });
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
    
    // Função para buscar as aliquotas de um dado código
    function getAliquotas(code) {
        if (piscofinsData.hasOwnProperty(code)) {
            return piscofinsData[code];
        } else {
            return null; // ou qualquer outro valor padrão
        }
    }  
     
});

function notify(from, align, icon, type, animIn, animOut, title, message){
    $.growl({
        icon: icon,
        title: title,
        message: message,
        url: ''
    },{
        element: 'body',
        type: type,
        allow_dismiss: true,
        placement: {
            from: from,
            align: align
        },
        offset: {
            x: 30,
            y: 30
        },
        spacing: 10,
        z_index: 999999,
        delay: 2500,
        timer: 1000,
        url_target: '_blank',
        mouse_over: false,
        animate: {
            enter: animIn,
            exit: animOut
        },
        icon_type: 'class',
        template: '<div data-growl="container" class="alert" role="alert">' +
        '<button type="button" class="close" data-growl="dismiss">' +
        '<span aria-hidden="true">&times;</span>' +
        '<span class="sr-only">Close</span>' +
        '</button>' +
        '<span data-growl="icon"></span>' +
        '<span data-growl="title"></span>' +
        '<span data-growl="message"></span>' +
        '<a href="#" data-growl="url"></a>' +
        '</div>'
    });
};

// Você pode opcionalmente adicionar a função ao escopo global explicitamente
window.notify = notify;



