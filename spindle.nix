{ pkgs ? import <nixpkgs> {} }:

let
  zensical = pkgs.zensical;
in
{
  pipelines.docs = {
    on.push.branches = [ "main" ];
    
    tasks = [
      {
        name = "manifest-hexanomicon-docs";
        
        # Declarative environment: Zensical and Git are 'just there'
        packages = [ 
          zensical 
          pkgs.git 
        ];
        
        script = ''
          # The binary is already in the $PATH. We build the site.
          zensical build
          
          # We move the resulting 'site' folder to the pages branch.
          # Tangled handles the 'Sites' deployment from here.
          tangled-deploy --dir ./site --branch pages
        '';
      }
    ];
  };
}