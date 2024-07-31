document.addEventListener('DOMContentLoaded', function() {
    // Pega os parâmetros da URL e preenche os campos do formulário
    var url = new URL(window.location.href);
    var urlParams = new URLSearchParams(window.location.search);
    var fields = [
        'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'cst_icms',
        'icms_aliquota', 'icms_aliquota_reduzida', 'cbenef', 'protege',
        'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita'
    ];

    fields.forEach(function(field) {
        if (urlParams.has(field)) {
            document.getElementById('search_' + field).value = urlParams.get(field);
        }
    });
});

document.getElementById('clearSearch').addEventListener('click', function() {
    // Obtém a URL sem os parâmetros da query string
    const baseUrl = window.location.origin + window.location.pathname;

    // Redefine a URL sem os parâmetros da query string
    window.history.replaceState(null, null, baseUrl);

    // Recarrega a página sem os parâmetros da query string
    window.location.reload();
});      

function addRow(button) {
    // Clone the form row
    const formRow = button.parentNode.parentNode;
    const newFormRow = formRow.cloneNode(true);

    // Clear the input value in the cloned row
    newFormRow.querySelector('input').value = '';

    // Update the button to be a remove button
    const newButton = newFormRow.querySelector('button');
    newButton.textContent = '-';
    newButton.classList.remove('btn-primary');
    newButton.classList.add('btn-danger');
    newButton.setAttribute('onclick', 'removeRow(this)');

    // Append the new row to the form container
    document.getElementById('form-container').appendChild(newFormRow);
}

function removeRow(button) {
    // Remove the form row
    const formRow = button.parentNode.parentNode;
    formRow.parentNode.removeChild(formRow);
}

document.getElementById('applySearch').addEventListener('click', function() {
    const rows = document.querySelectorAll('#form-container .form-row');
    const params = new URLSearchParams();

    rows.forEach(row => {
        const select = row.querySelector('select').value;
        const input = row.querySelector('input').value;
        if (select && input) {
            params.append(select, input);
        }
    });

    window.location.search = params.toString();
});

function getQueryParams() {
    const params = {};
    const queryString = window.location.search.slice(1);
    const queries = queryString.split('&');

    queries.forEach(query => {
        const [key, value] = query.split('=');
        if (key && value) {
            if (!params[key]) {
                params[key] = [];
            }
            params[key].push(decodeURIComponent(value));
        }
    });

    return params;
}

document.addEventListener('DOMContentLoaded', () => {
    const queryParams = getQueryParams();
    let isFirstRow = true; 

    Object.keys(queryParams).forEach((key, index) => {
        queryParams[key].forEach(value => {
            const formRow = document.querySelector('#form-container .form-row');
            const newFormRow = formRow.cloneNode(true);
            newFormRow.querySelector('select').value = key;
            newFormRow.querySelector('input').value = value;

            const newButton = newFormRow.querySelector('button');
            if (isFirstRow) {
                newButton.textContent = '+';
                newButton.classList.add('btn-primary');
                newButton.classList.remove('btn-danger');
                newButton.setAttribute('onclick', 'addRow(this)');  
                isFirstRow = false;            
            } else {
                newButton.textContent = '-';
                newButton.classList.remove('btn-primary');
                newButton.classList.add('btn-danger');
                newButton.setAttribute('onclick', 'removeRow(this)');
            }

            document.getElementById('form-container').appendChild(newFormRow);
        });
    });

    // Remove the initial form row if queryParams are present
    if (Object.keys(queryParams).length > 0) {
        const initialFormRow = document.querySelector('#form-container .form-row');
        initialFormRow.parentNode.removeChild(initialFormRow);
    }
});