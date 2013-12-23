function check(input) {
	var $input = $(input);
	var className = $input.attr('class');
	var number, check;
	if ($input.attr('checked')) {
		check = 'check';
	} else {
		check = 'uncheck'
	}
	number = parseInt(className.substring(check.length, className.length));
	console.log(check);
	console.log(number);

	//TODO 1 body를 얻어온다
	//[ ] regex를 써서 number번째를 구한다
	//바꾼후 PUT한다
	//브라우저 리로드

	//console.log(input);
	//console.log($(input).attr('class'));
}