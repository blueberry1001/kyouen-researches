import Lake
open Lake DSL

package «kyouen-1-to-9-classification» where

lean_lib Kyouen where

@[default_target]
lean_exe «kyouen-classification-demo» where
  root := `Main
