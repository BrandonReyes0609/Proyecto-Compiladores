# Proyecto-Compiladores

El proyecto de compiladores


Para crear la imagen de docker si no existe

`docker build --rm . -t csp-image`

Para ingresar a la imagen de docker

`docker run --rm -ti -v "${PWD}/program:/program" csp-image`

Deviras de entrar al contenedor

`appuser@33497f74966c:/program$ []`
