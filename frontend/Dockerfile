# ./frontend/Dockerfile
#FROM php:8.0-apache
#RUN docker-php-ext-install pdo pdo_mysql
#COPY . /var/www/html/


# frontend/Dockerfile
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/

# Copy web files
COPY . /var/www/html/

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]