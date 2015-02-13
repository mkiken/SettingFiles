/*****************************************************************************
 * The contents of this file are subject to the RECIPROCAL PUBLIC LICENSE
 * Version 1.1 ("License"); You may not use this file except in compliance
 * with the License. You may obtain a copy of the License at
 * http://opensource.org/licenses/rpl.php. Software distributed under the
 * License is distributed on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND,
 * either express or implied.
 *
 * @author:  Mr. Milk (aka Marcelo Leite)
 * @email:   mrmilk@anysoft.com.br
 * @version: 1.0
 * @date:    2007-11-22
 *
 *****************************************************************************/
function phpStylist() {

	php_path     = "C:\\Program Files\\xampp\\php\\php.exe";
	stylist_path = "C:\\Program Files\\xampp\\htdocs\\phpStylist.php";
	params = "";
	
  //Indentation and General Formatting:
	params += "--indent_size 2 ";
	//params += "--indent_with_tabs ";
	//params += "--keep_redundant_lines ";
	//params += "--space_inside_parentheses ";
	//params += "--space_outside_parentheses ";
	params += "--space_after_comma ";
	
  //Operators:
	params += "--space_around_assignment ";
	params += "--align_var_assignment ";
	params += "--space_around_comparison ";
	params += "--space_around_arithmetic ";
	params += "--space_around_logical ";
	params += "--space_around_colon_question ";
	
  //Functions, Classes and Objects:
	params += "--line_before_function ";
	params += "--line_before_curly_function ";
	//params += "--line_after_curly_function ";
	//params += "--space_around_obj_operator ";
	//params += "--space_around_double_colon ";
	
  //Control Structures:
	params += "--space_after_if ";
	//params += "--else_along_curly ";
	//params += "--line_before_curly ";
	params += "--add_missing_braces ";
	params += "--line_after_break ";
	params += "--space_inside_for ";
	params += "--indent_case ";
	
	//Arrays and Concatenation:
	//params += "--line_before_array ";
	params += "--vertical_array ";
	params += "--align_array_assignment ";
	params += "--space_around_double_arrow ";
	//params += "--vertical_concat ";
	//params += "--space_around_concat ";
	
	//Comments:
	params += "--line_before_comment_multi ";
	//params += "--line_after_comment_multi ";
	params += "--line_before_comment ";
	//params += "--line_after_comment ";

  var ed = newEditor();
  ed.assignActiveEditor();
  var cx = ed.caretX();
  var cy = ed.caretY();
  var fni = ed.fileName();
  var fno = fni+".cb.php";
  if(!fni.match(/\.php$/)) {
		echo("NOT A PHP FILE!");
		return;
	}
  fni = fni+".tmp.php";
  edt = newEditor();
  edt.newFile(fni);
  if(ed.selText()=='') {
    edt.text(ed.Text());
  }
  else {
    edt.text(ed.selText());
  }
  edt.saveFile();
  var sh = new ActiveXObject("WScript.shell");
  var fs = new ActiveXObject("Scripting.FileSystemObject");
  sh.run('cmd /c ""'+php_path+'" -f "'+stylist_path+'" "'+fni+'" '+params+' > "'+fno+'""', 0, true);
  edt.openFile(fno);
  var txt = edt.Text();
  edt.closeFile();
  fs.DeleteFile(fno);
  fs.DeleteFile(fni);
  if(ed.selText()=='') {
    ed.Text(txt);
  }
  else {
    txt = txt.substr(7, txt.length-10);
    ed.selText(txt);
  }
  ed.caretX(cx);
  ed.caretY(cy);

}

function Init(){
  addMenuItem("phpStylist", "", "phpStylist", "CTRL+B");
}
