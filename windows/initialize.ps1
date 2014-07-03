# PowerShellでもコマンドを実行できるようにする
Set-ExecutionPolicy RemoteSigned

$SET = "${HOME}\Desktop\repository\SettingFiles"

cmd /c mklink /d ${HOME}\AppData\Roaming\.emacs.d ${SET}\.emacs.d

# New-Item ?Path $Profile ?Type File ?Force
cmd /c mklink $profile ${SET}\windows\powershell_profile.ps1

cmd /c mklink ${HOME}\.gitconfig ${SET}\gitfiles\.gitconfig
cp ${SET}\gitfiles\.gitconfig.local_windows ${HOME}\.gitconfig.local
echo "You can write LOCAL settings for git to '${HOME}\.gitconfig.local'."

New-Item "${HOME}\local_profile.ps1" -itemType File
echo "You can write LOCAL settings for PowerShell to '${HOME}\local_profile.ps1'."
