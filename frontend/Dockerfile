# Usar uma imagem base oficial do Node.js
FROM node:20-alpine

# Definir o diretório de trabalho no container
WORKDIR /app

# Copiar package.json e package-lock.json
COPY package*.json ./

# Instalar as dependências
RUN npm ci

# Copiar o restante do código da aplicação
COPY . .

# Build da aplicação para produção
RUN npm run build

# Instalar um servidor web simples para servir os arquivos estáticos
RUN npm install -g serve

# Expor a porta que a aplicação vai rodar
EXPOSE 3000

# Comando para servir a aplicação em produção
CMD ["serve", "-s", "build", "-l", "3000"]
