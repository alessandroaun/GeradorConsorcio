; --- INICIO DO SCRIPT ---

#define MyAppName "Gerenciador Simulador Recon"
#define MyAppVersion "1.0"
#define MyAppPublisher "Alessandro Uchoa"
#define MyAppExeName "GerenciadorSimuladorRecon.exe"

[Setup]
; ID único do App (Gere um novo no Inno Setup em Tools > Generate GUID se quiser)
AppId={{A3D24891-B789-4D6E-9012-ABCDEF123456}

; Nome e Versão
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

; ONDE VAI INSTALAR: {sd} significa System Drive (geralmente C:)
; Vai criar C:\SimuladorRecon
DefaultDirName={sd}\Gerenciador Simulador Recon

; Bloqueia o usuário de mudar a pasta (opcional, remova se quiser permitir)
DisableDirPage=no

; Nome do grupo no Menu Iniciar
DefaultGroupName={#MyAppName}

; Permissões Administrativas (Necessário para escrever no C:\)
PrivilegesRequired=admin

; Pasta onde o instalador final será salvo
OutputDir=.\Output_Instalador
OutputBaseFilename=Instalador_GerenciadorSimuladorRecon_v1

; Ícone do instalador (se tiver um .ico, descomente a linha abaixo)
SetupIconFile="C:\Users\aless\Desktop\SoftRecon\GeradorConsorcio\logo_app_recon.ico"

; Compressão
Compression=lzma
SolidCompression=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 1. O EXECUTÁVEL PRINCIPAL (Aponte para onde está seu .exe gerado pelo PyInstaller)
; IMPORTANTE: Ajuste o caminho "Source" abaixo para a pasta do seu PC
Source: "C:\Users\aless\Desktop\SoftRecon\GeradorConsorcio\dist\GerenciadorSimuladorRecon.exe"; DestDir: "{app}"; Flags: ignoreversion

; 2. ARQUIVOS DE DADOS (users.dat e secret.key)
; O Flag "onlyifdoesntexist" é VITAL. Ele impede que o instalador sobrescreva
; os usuários se você lançar uma atualização futura.
Source: "C:\Users\aless\Desktop\SoftRecon\GeradorConsorcio\dist\users.dat"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "C:\Users\aless\Desktop\SoftRecon\GeradorConsorcio\dist\secret.key"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
; Cria o atalho no Menu Iniciar
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; Cria o atalho na Área de Trabalho
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Opção para rodar o programa ao terminar a instalação
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

; --- FIM DO SCRIPT ---