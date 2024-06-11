$(document).ready(function(){
			// Validation
			$( "#j-pro" ).justFormsPro({
				rules: {
					file_name: {
						validate: true,
						required: true,
						size: 1,
						extension: "csv"
					}
				},
				messages: {
					file_name: {
						size_extension: "Somente arquivo CSV. Size: 1Mb",
					}
				}
			});
		});