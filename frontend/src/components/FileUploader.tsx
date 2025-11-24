import React, { useRef, useState } from 'react';
import { API_BASE_URL } from '../services/api';

interface FileUploaderProps {
  label: string;
  accept: string;
  maxSize?: number; // em MB
  currentFile?: string;
  onFileSelect: (file: File | null) => void;
  onRemove?: () => void;
  placeholder?: string;
  instructions?: string[];
  disabled?: boolean;
  className?: string;
}

const FileUploader: React.FC<FileUploaderProps> = ({
  label,
  accept,
  maxSize = 10,
  currentFile,
  onFileSelect,
  onRemove,
  placeholder = "Nenhum arquivo selecionado",
  instructions = [],
  disabled = false,
  className = ""
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validar tipo de arquivo
    const acceptedTypes = accept.split(',').map(type => type.trim());
    const isValidType = acceptedTypes.some(type => {
      if (type.startsWith('.')) {
        return file.name.toLowerCase().endsWith(type.toLowerCase());
      }
      return file.type.match(type.replace('*', '.*'));
    });

    if (!isValidType) {
      alert(`Tipo de arquivo não permitido. Use apenas: ${accept}`);
      return;
    }

    // Validar tamanho
    if (file.size > maxSize * 1024 * 1024) {
      alert(`Arquivo muito grande. Máximo permitido: ${maxSize}MB`);
      return;
    }

    setIsUploading(true);

    try {
      // Criar preview para imagens
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          setPreviewUrl(e.target?.result as string);
        };
        reader.readAsDataURL(file);
      } else {
        setPreviewUrl(null);
      }

      onFileSelect(file);
    } catch (error) {
      console.error('Erro ao processar arquivo:', error);
      alert('Erro ao processar arquivo. Tente novamente.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemove = () => {
    setPreviewUrl(null);
    onFileSelect(null);
    if (onRemove) onRemove();
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const getFileIcon = () => {
    if (accept.includes('image/')) {
      return (
        <svg className="w-6 h-6 sm:w-8 sm:h-8 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      );
    } else if (accept.includes('.p12') || accept.includes('.pfx')) {
      return (
        <svg className="w-6 h-6 sm:w-8 sm:h-8 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      );
    }
    return (
      <svg className="w-6 h-6 sm:w-8 sm:h-8 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    );
  };

  return (
    <div className={`space-y-3 sm:space-y-4 ${className}`}>
      <div className="flex items-center justify-between">
        <h4 className="text-sm sm:text-md font-medium text-text">{label}</h4>
        <span className="text-xs sm:text-sm text-text-muted">{accept.replace(/\*/g, '').toUpperCase()} até {maxSize}MB</span>
      </div>

      {/* Preview do arquivo */}
      <div className="flex items-center space-x-3 sm:space-x-4 p-3 sm:p-4 border border-border rounded-lg bg-surface">
        <div className="w-12 h-12 sm:w-16 sm:h-16 border-2 border-dashed border-border rounded-lg flex items-center justify-center overflow-hidden flex-shrink-0">
          {previewUrl ? (
            accept.includes('image/') ? (
              <img
                src={previewUrl}
                alt="Preview"
                className="w-full h-full object-contain"
              />
            ) : (
              <svg className="w-8 h-8 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )
          ) : currentFile ? (
            accept.includes('image/') && currentFile.startsWith('/files/') ? (
              <img
                src={`${API_BASE_URL}${currentFile}`}
                alt="Arquivo atual"
                className="w-full h-full object-contain"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  const parent = target.parentElement;
                  if (parent) {
                    parent.innerHTML = `
                      <svg class="w-8 h-8 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                      </svg>
                    `;
                  }
                }}
              />
            ) : (
              <svg className="w-8 h-8 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )
          ) : (
            getFileIcon()
          )}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm text-text font-medium truncate">
            {currentFile
              ? (currentFile.startsWith('/files/') || currentFile.startsWith('/secure/'))
                ? currentFile.split('/').pop() || "Arquivo enviado"
                : currentFile.split('/').pop() || currentFile
              : (previewUrl ? "Arquivo selecionado" : placeholder)}
          </p>
          <p className="text-xs text-text-muted mt-1">
            {currentFile
              ? "Arquivo já enviado anteriormente"
              : "Clique em fazer upload para selecionar um arquivo"
            }
          </p>
        </div>
      </div>

      {/* Controles */}
      <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          onChange={handleFileSelect}
          className="hidden"
          disabled={disabled}
        />

        <button
          onClick={disabled ? undefined : handleUploadClick}
          disabled={disabled || isUploading}
          className={`px-2 py-1.5 sm:px-3 sm:py-2 lg:px-4 lg:py-2 text-xs sm:text-sm lg:text-base bg-primary text-white rounded-md sm:rounded-lg hover:bg-primaryDark transition-colors flex items-center justify-center ${
            disabled ? "cursor-not-allowed opacity-50" : ""
          }`}
        >
          {isUploading ? (
            <div className="flex items-center space-x-2">
              <svg
                className="animate-spin h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span className="text-sm">Enviando...</span>
            </div>
          ) : (
            <>
              <svg
                className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <span className="hidden sm:inline">
                {currentFile || previewUrl ? "Alterar Arquivo" : "Fazer Upload"}
              </span>
              <span className="sm:hidden">
                {currentFile || previewUrl ? "Alterar" : "Upload"}
              </span>
            </>
          )}
        </button>

        {(currentFile || previewUrl) && (
          <button
            onClick={disabled ? undefined : handleRemove}
            disabled={disabled}
            className={`px-2 py-1.5 sm:px-3 sm:py-2 lg:px-4 lg:py-2 text-xs sm:text-sm lg:text-base border border-error text-error rounded-md sm:rounded-lg hover:bg-error hover:text-background transition-colors flex items-center justify-center ${
              disabled ? "cursor-not-allowed opacity-50" : ""
            }`}
          >
            <svg
              className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
            <span className="hidden sm:inline">Remover</span>
            <span className="sm:hidden">Excluir</span>
          </button>
        )}
      </div>

      {/* Instruções */}
      {instructions.length > 0 && (
        <div className="text-xs sm:text-xs text-text-muted space-y-1">
          {instructions.map((instruction, index) => (
            <p key={index}>• {instruction}</p>
          ))}
        </div>
      )}
    </div>
  );
};

export default FileUploader;