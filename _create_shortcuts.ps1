$ErrorActionPreference = 'Stop'
$W = New-Object -ComObject WScript.Shell

$target  = 'D:\anaconda\envs\chroma\pythonw.exe'
$args    = '"D:\chroma_ui\desktop_app.py"'
$workdir = 'D:\chroma_ui'
$icon    = 'D:\anaconda\envs\chroma\pythonw.exe,0'
$desc    = '历史研究 RAG 检索 —— 打开即启动服务，关闭即停止'

$desktop = [Environment]::GetFolderPath('Desktop')
$start   = [Environment]::GetFolderPath('Programs')

foreach ($dir in @($desktop, $start)) {
    $lnk = $W.CreateShortcut((Join-Path $dir '历史研究 RAG 检索.lnk'))
    $lnk.TargetPath        = $target
    $lnk.Arguments         = $args
    $lnk.WorkingDirectory  = $workdir
    $lnk.IconLocation      = $icon
    $lnk.Description       = $desc
    $lnk.Save()
}
Write-Output ('OK -> ' + $desktop)
Write-Output ('OK -> ' + $start)
