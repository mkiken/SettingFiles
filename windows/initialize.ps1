$SET = "${HOME}\Desktop\repository\SettingFiles"

cmd /c mklink /d ${HOME}\AppData\Roaming\.emacs.d ${SET}\.emacs.d

# New-Item ?Path $Profile ?Type File ?Force

cmd /c mklink $profile ${SET}\windows\powershell_profile.ps1

cmd /c mklink ${HOME}\.gitconfig ${SET}\gitfiles\.gitconfig
