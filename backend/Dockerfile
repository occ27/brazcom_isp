# Usar uma imagem base oficial do Python
FROM python:3.11-slim

# Definir o diretório de trabalho no container
WORKDIR /app

# Instalar dependências do sistema necessárias para compilar pacotes nativos
# (mysqlclient, lxml, cryptography, etc.). Mantemos camadas pequenas e removemos
# caches ao final para reduzir o tamanho da imagem.
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	build-essential \
	pkg-config \
	python3-dev \
	default-libmysqlclient-dev \
	libxml2-dev \
	libxslt1-dev \
	libssl-dev \
	libffi-dev \
	gcc \
	# Dependências do xmlsec (necessárias para python-xmlsec)
	libxmlsec1-dev \
	libxmlsec1-openssl \
	xmlsec1 \
	cron \
	&& rm -rf /var/lib/apt/lists/*

# Copiar o arquivo de dependências
COPY requirements.txt .

# Instalar ferramentas de build primeiro
RUN python3 -m pip install --no-cache-dir --upgrade pip wheel setuptools

# Instalar as dependências do projeto
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Rebuild lxml and xmlsec from source contra bibliotecas do sistema
RUN python3 -m pip uninstall -y lxml xmlsec || true
RUN python3 -m pip install --no-cache-dir --no-binary=:all: lxml xmlsec

# Copiar o restante do código da aplicação
COPY . .

# Copy cron files and set permissions
COPY crontab /etc/cron.d/scheduler-cron
COPY scheduler-entrypoint.sh /scheduler-entrypoint.sh
RUN chmod 0644 /etc/cron.d/scheduler-cron && \
    chmod +x /scheduler-entrypoint.sh && \
    sed -i 's/\r$//' /scheduler-entrypoint.sh

# Expor a porta que a aplicação vai rodar
EXPOSE 8000

# Comando para iniciar a aplicação com Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
