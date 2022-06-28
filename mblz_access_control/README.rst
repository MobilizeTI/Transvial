==============
MBLZ: Control de Accesos
==============

Este módulo permite gestionar los derechos de acceso de los usuarios mediante perfiles.

Los grupos de Odoo son un conjunto coherente de reglas que son funcionalmente consistentes. Los perfiles permiten combinar varios grupos y adaptar eficazmente el acceso de los usuarios a cada uno de ellos.

Aquí un ejemplo :

* Grupo supervisor de MTTO: crear una OT, modificar una OT, cancelar una OT, etc.
* Grupo técnico de MTTO: actualizar un OT y sus tareas asociadas

El administrador general de la empresa (ejem: Mueve Fontibon) probablemente pertenezca a ambos grupos. **mblz_access_control** permite combinar ambos grupos en un solo perfil.

Es una forma alternativa de gestionar los derechos de los usuarios por perfiles funcionales.

Básicamente, un « perfil » es un usuario inactivo ficticio (res.users) etiquetado como perfil.

Significa que como antes (con las reglas básicas de Odoo), se puede añadir grupos a un perfil.

Características:

* Puede asociar un perfil a los usuarios creados.
* Puede añadir usuarios por perfil.
* Puede establecer los campos a actualizar para los usuarios asociados.
* Tiene la opción de actualizar o no en modo de escritura para los usuarios asociados,  con el campo 'Actualizar los usuarios después de la creación' en los perfiles.
* Puede ocultar menus especificos
* Puede restringir el acceso al módo desarrollor por perfil o usuario
* Puede restringir el acceso al botón de **Impresión** por perfil o usuario
* Puede restringir el acceso al botón de **Acción por** perfil o usuario

**Índice de contenidos**

.. contents::
   :local:

Configuración
=============

Para configurar este módulo, es necesario:

* Ir al nuevo menú **Configuración > Usuarios y Compañías > Perfiles de Usuario** y crear los
  perfiles que necesite.

Uso
=====

* Vaya al nuevo menú **Configuración > Usuarios y Compañías > Usuarios** y cree un nuevo
  usuario, elija el perfil y después de guardar tendrá los derechos de acceso del usuario establecidos.

