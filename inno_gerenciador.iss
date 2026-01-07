; --- INICIO DO SCRIPT ATUALIZADO ---

#define MyAppName "Gerenciador Simulador Recon"
; IMPORTANTE: Sempre mude a vers�o aqui quando gerar um novo instalador (ex: 1.1, 1.2)
#define MyAppVersion "1.0.4" 
#define MyAppPublisher "Alessandro Uchoa"
#define MyAppExeName "GerenciadorSimuladorRecon.exe"

[Setup]
; ID �nico do App
AppId={{A3D24891-B789-4D6E-9012-ABCDEF123456}

; Informa��es B�sicas
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

; --- DIRETIVAS DE ATUALIZA��O (NOVAS) ---
; Tenta fechar o aplicativo se ele estiver rodando antes de instalar
CloseApplications=yes
; Se n�o conseguir fechar suavemente, for�a o fechamento
CloseApplicationsFilter=*.exe
; N�o pergunta se pode usar a pasta existente (vital para updates)
DirExistsWarning=no
; ----------------------------------------

; Diret�rio de Instala��o (C:\Gerenciador Simulador Recon)
DefaultDirName={sd}\Gerenciador Simulador Recon
DisableDirPage=no
DefaultGroupName={#MyAppName}

; Permiss�es para instalar
PrivilegesRequired=admin

; Sa�da do Instalador
OutputDir=.\Output_Instalador
; DICA: O nome do arquivo de sa�da pode incluir a vers�o para facilitar
OutputBaseFilename=Setup_GerenciadorSimuladorRecon_v{#MyAppVersion}

; �cone
SetupIconFile="C:\Users\aless\Desktop\SoftRecon\GeradorConsorcio\logo_recon-consorcio.ico"

; Compress�o
Compression=lzma
SolidCompression=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Dirs]
; Garante que a pasta criada tenha permiss�o de escrita para todos os usu�rios
; Isso evita erros ao salvar logs ou atualizar o users.dat
Name: "{app}"; Permissions: users-modify

[Files]
; 1. O EXECUT�VEL PRINCIPAL
Source: "C:\Users\aless\Desktop\SoftRecon\GeradorConsorcio\dist\GerenciadorSimuladorRecon.exe"; DestDir: "{app}"; Flags: ignoreversion

; 2. ARQUIVOS DE DADOS QUE N�O DEVEM SER SUBSTITU�DOS
; 'onlyifdoesntexist': S� copia se o arquivo n�o existir (preserva dados do usu�rio)
; 'uninsneveruninstall': N�o deleta esses arquivos se desinstalar (backup de seguran�a)
Source: "C:\Users\aless\Desktop\SoftRecon\GeradorConsorcio\dist\users.dat"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "C:\Users\aless\Desktop\SoftRecon\GeradorConsorcio\dist\secret.key"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Roda o programa ao finalizar
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

; --- FIM DO SCRIPT ---