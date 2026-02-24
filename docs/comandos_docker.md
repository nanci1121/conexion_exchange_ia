# 🐳 Docker en WSL2 — Windows 11

Guía de referencia rápida para trabajar con Docker dentro de WSL2 en Windows 11.

---

## 📦 Instalación y configuración inicial

### 1. Instalar WSL2 (desde PowerShell como administrador)
```powershell
wsl --install
wsl --set-default-version 2
```

### 2. Instalar Docker Desktop (recomendado)
- Descarga desde: https://www.docker.com/products/docker-desktop/
- Durante la instalación, activa la opción **"Use WSL 2 based engine"**
- En **Settings → Resources → WSL Integration**, activa tu distribución de Linux

### 3. Instalar Docker directamente en WSL2 (sin Docker Desktop)
```bash
# Actualizar paquetes
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y ca-certificates curl gnupg lsb-release

# Agregar la clave GPG oficial de Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Agregar el repositorio de Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Agregar tu usuario al grupo docker (evita usar sudo en cada comando)
sudo usermod -aG docker $USER
newgrp docker

# Iniciar el servicio Docker
sudo service docker start
```

---

## ✅ Verificación

```bash
# Verificar versión de Docker
docker --version

# Verificar que Docker funciona correctamente
docker run hello-world

# Ver información del sistema Docker
docker info
```

---

## 🖼️ Imágenes

```bash
# Listar imágenes locales
docker images

# Buscar una imagen en Docker Hub
docker search nginx

# Descargar una imagen
docker pull nginx
docker pull ubuntu:22.04

# Eliminar una imagen
docker rmi nginx

# Eliminar todas las imágenes sin uso
docker image prune -a

# Construir una imagen desde un Dockerfile
docker build -t mi-app:1.0 .

# Etiquetar una imagen
docker tag mi-app:1.0 usuario/mi-app:1.0

# Subir una imagen a Docker Hub
docker login
docker push usuario/mi-app:1.0
```

---

## 📦 Contenedores

```bash
# Crear y ejecutar un contenedor
docker run nginx

# Ejecutar en segundo plano (detached)
docker run -d nginx

# Ejecutar con nombre personalizado
docker run -d --name mi-nginx nginx

# Ejecutar con mapeo de puertos (host:contenedor)
docker run -d -p 8080:80 nginx

# Ejecutar con variables de entorno
docker run -d -e MYSQL_ROOT_PASSWORD=secreto mysql

# Ejecutar con volumen montado
docker run -d -v /ruta/local:/ruta/contenedor nginx

# Ejecutar con terminal interactiva
docker run -it ubuntu bash

# Ejecutar y eliminar el contenedor al terminar
docker run --rm ubuntu echo "Hola mundo"

# Listar contenedores en ejecución
docker ps

# Listar todos los contenedores (incluidos detenidos)
docker ps -a

# Detener un contenedor
docker stop mi-nginx

# Iniciar un contenedor detenido
docker start mi-nginx

# Reiniciar un contenedor
docker restart mi-nginx

# Eliminar un contenedor (debe estar detenido)
docker rm mi-nginx

# Forzar eliminación de un contenedor en ejecución
docker rm -f mi-nginx

# Eliminar todos los contenedores detenidos
docker container prune
```

---

## 🔍 Inspección y logs

```bash
# Ver logs de un contenedor
docker logs mi-nginx

# Ver logs en tiempo real
docker logs -f mi-nginx

# Ver últimas N líneas de logs
docker logs --tail 50 mi-nginx

# Inspeccionar detalles de un contenedor
docker inspect mi-nginx

# Ver estadísticas de uso de recursos en tiempo real
docker stats

# Ver procesos dentro de un contenedor
docker top mi-nginx

# Ejecutar un comando dentro de un contenedor en ejecución
docker exec mi-nginx ls /etc/nginx

# Abrir una terminal dentro de un contenedor en ejecución
docker exec -it mi-nginx bash
```

---

## 💾 Volúmenes

```bash
# Crear un volumen
docker volume create mis-datos

# Listar volúmenes
docker volume ls

# Inspeccionar un volumen
docker volume inspect mis-datos

# Usar un volumen en un contenedor
docker run -d -v mis-datos:/var/lib/mysql mysql

# Eliminar un volumen
docker volume rm mis-datos

# Eliminar volúmenes sin uso
docker volume prune
```

---

## 🌐 Redes

```bash
# Listar redes
docker network ls

# Crear una red
docker network create mi-red

# Conectar un contenedor a una red
docker network connect mi-red mi-nginx

# Desconectar un contenedor de una red
docker network disconnect mi-red mi-nginx

# Ejecutar un contenedor en una red específica
docker run -d --network mi-red --name app mi-app

# Eliminar una red
docker network rm mi-red

# Eliminar redes sin uso
docker network prune
```

---

## 🐙 Docker Compose

```bash
# Levantar los servicios definidos en docker-compose.yml
docker compose up

# Levantar en segundo plano
docker compose up -d

# Construir imágenes antes de levantar
docker compose up --build

# Detener y eliminar contenedores, redes y volúmenes
docker compose down

# Detener y eliminar incluyendo volúmenes
docker compose down -v

# Ver estado de los servicios
docker compose ps

# Ver logs de todos los servicios
docker compose logs

# Ver logs en tiempo real
docker compose logs -f

# Ejecutar un comando en un servicio
docker compose exec web bash

# Escalar un servicio (ej: 3 instancias de web)
docker compose up -d --scale web=3
```

### Ejemplo de `docker-compose.yml`
```yaml
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
    volumes:
      - ./html:/usr/share/nginx/html
    networks:
      - mi-red

  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: secreto
      MYSQL_DATABASE: mi_base
    volumes:
      - db-data:/var/lib/mysql
    networks:
      - mi-red

volumes:
  db-data:

networks:
  mi-red:
```

---

## 🧹 Limpieza general

```bash
# Eliminar todos los recursos sin uso (contenedores, imágenes, redes, volúmenes)
docker system prune

# Limpieza total incluyendo volúmenes
docker system prune -a --volumes

# Ver uso de espacio en disco de Docker
docker system df
```

---

## ⚙️ Configuración específica para WSL2

### Iniciar Docker automáticamente al abrir WSL2
Agrega esto al final de tu `~/.bashrc` o `~/.zshrc`:
```bash
# Iniciar Docker si no está corriendo
if [ $(service docker status | grep -c "not running") -gt 0 ]; then
  sudo service docker start
fi
```

### Acceder a archivos de Windows desde WSL2
Los discos de Windows están montados en `/mnt/`:
```bash
# Acceder al disco C:
cd /mnt/c/Users/TuUsuario

# Montar un volumen desde una ruta de Windows
docker run -v /mnt/c/mis-proyectos/app:/app node:18 node app.js
```

### Acceder a un contenedor desde el navegador de Windows
Los puertos publicados en WSL2 son accesibles directamente desde Windows:
```
http://localhost:8080
```

### Permitir ejecutar Docker sin sudo (si es necesario)
```bash
sudo usermod -aG docker $USER
# Cierra y vuelve a abrir la terminal WSL2
```

---

## 📝 Dockerfile — Referencia rápida

```dockerfile
# Imagen base
FROM node:18-alpine

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar archivos de dependencias
COPY package*.json ./

# Instalar dependencias
RUN npm install

# Copiar el resto del código
COPY . .

# Exponer el puerto
EXPOSE 3000

# Variables de entorno
ENV NODE_ENV=production

# Comando por defecto al iniciar el contenedor
CMD ["node", "server.js"]
```

---

*Documentación oficial: https://docs.docker.com*