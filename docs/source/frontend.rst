########
Frontend
########

Below, we'll walk through the frontend portion of the codebase written in 
React.

***********
Compilation
***********

The frontend codebase uses the create-react-app starter as the base, so as to 
ease the configuration process. As of current, we use an add-on called 
``customize-cra`` to customize some of the webpack features that we need, so that
we don't have to 'eject' from create-react-app just to use those functionality.

Features that we use as of current:
- ``babelInclude`` - this is to include compilation of our open-source design 
system, as we do not precompile the design system before releasing an npm 
package.
- ``addWebpackExternals`` - this allows us to exclude certain packages from the 
webpack compilation. Right now, we are excluding React, ReactDOM, and ReactRedux
as these packages are depended on for both the closed source portion of the
code. 

******************************
Closed-source Code Compilation
******************************

We integrate Orchestra with our closed-source product, and we had to figure out
a way to inject closed source components in the open source world. Here are some
advice on how you can implement this feature.

The closed source portion of the codebase would be compiled, and the compiled 
scripts would be included in the open source portion of the codebase. We include
these scripts programmatically, by injecting the script tags into the compiled
``index.html`` You can customize which scripts to be injected by modifying the 
``orchestra/settings.py`` file. 

We run these urls through a ``static`` template tag function to link the closed
source assets up. Through the views.py, we inject these scripts into the 
``index.html``.

As for using the closed source component in the open sourced codebase, we inject
the components in the ``window.orchestra`` global object in the closed source
portion, and we refer to the relevant components that we want to use through the
global object. These closed source components would have access to the Redux
state since the objects are nested in the DOM with the Redux provider, and hence
selectors and dispatches can be used easily.
