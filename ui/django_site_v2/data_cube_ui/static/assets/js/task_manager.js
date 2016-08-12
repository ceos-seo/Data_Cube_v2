$(document).ready(function() {
    $('#query-list-table-full')
    	.on('draw.dt', function() {applyEvenAndOddClasses();})
	.DataTable( {
	    "order": [[1, "asc"]],
	    "bLengthChange": false,
	    "bPaginate": true
	});
});

function applyEvenAndOddClasses() {
    var table = document.getElementById("query-list-table-full");
    for (var i = 0, row; row = table.rows[i]; i++) {
	if (i != 0 && i % 2 == 0) {
	    for (var j = 0, col; col = row.cells[j]; j++) {
		col.className='even';
	    }
	}
	else if (i != 0 && i % 2 != 0) {
	    for (var j = 0, col; col = row.cells[j]; j++) {
		col.className='odd';
	    }
	}
    }
}
