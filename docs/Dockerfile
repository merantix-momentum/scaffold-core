FROM europe-west4-docker.pkg.dev/mx-labs-devops/container-repository/nginx:latest

COPY _build/html /usr/share/nginx/html
RUN chmod -R a+r /usr/share/nginx/html
RUN chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /usr/share/nginx/html
