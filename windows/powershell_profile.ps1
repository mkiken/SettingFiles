$REPO = "${HOME}\Desktop\repository"
$SET = "${REPO}\SettingFiles"

Set-Alias ec "C:\Program Files\emacs-24.3\bin\emacsclientw"
Set-Alias em "C:\Program Files\emacs-24.3\bin\runemacs"
Set-Alias e "./a"
# Set-Alias grep "findstr"
Set-Alias ex "explorer"


Set-Alias g "git"

Set-Alias grunt "grunt.cmd"



# lsは簡易表示に
remove-item alias:ls -force
Set-Alias ls list-files-in-a-wide-format

# cdの際にls
remove-item alias:cd -force
function cd($arg){
  if($arg -eq $null){
   cdh
  } else{
    Set-Location $arg
    list-files-in-a-wide-format
  }
}

function grep($arg1, $arg2){
  findstr  /I $arg1 $arg2
}

function cdd(){cd ${HOME}\Desktop}
function cdh(){cd ${HOME}}
function cdrepo(){cd ${REPO}}
function cds(){cd ${SET}}
function up(){cd ..}
function gst(){git status}
function gps(){git push}
# function gpl(){git pull}
# function gci(){git commit}
function gaa(){git add .}
function winset(){em ${SET}\windows\powershell_profile.ps1}
function wininit() {em ${SET}\windows\initialize.ps1}


function la($arg){
 if($arg -eq $null){
     Get-ChildItem -force
  } else{
       Get-ChildItem -force $arg
  }
}

# 関数: list-files-in-a-wide-format
# http://subtech.g.hatena.ne.jp/h2u/20090428/1240893610
function list-files-in-a-wide-format($arg) {
  if($arg -eq $null){
    # Get-ChildItemをパイプでFormat-Wideに渡す
    get-childitem | format-wide name -force -autosize
  } else{
    get-childitem $arg | format-wide name -force -autosize
  }
  # 以上のコードは以下のようにも書ける
  # gci | fw name -a
}

$Env:Path += ";c:\MinGW\bin\"


# echo "alias set."
