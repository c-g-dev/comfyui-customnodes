# CGDev's custom nodes
ComfyUI nodes I've had had to make because I couldn't find them elsewhere. A lot of these are forks of other people's custom nodes with extended functionality.

Do NOt clone this into your customNodes repo, most of these will require manual injection.

## Loop, LoopStart, LoopEnd

These are a modded version of m99's loopback nodes. Those loops could not be exited, and required a restart of the ComfyUI backend to reset. These versions have added toggle to allow you to flush the loop data at will. Hit "flush = enabled" and rerun the queue to clean the loop. Set it back to "flush = disabled" to start looping again.

## SaveImageStatic, LoadImageStatic

Pulls and saves image from/to a static path. The difference between these and other implementations is that they take in a "filepath" string node dependency. The idea is that you define an input filepath as a static configuration in some other node and then define the filename of the file you want to pull here. You will need some way of sending in the filepath string. I'm using the WAS-Suite String to Text node.

## Preview Bridge with Mask Freeze

A mod of the Impact Pack's "Preview Bridge". In the original node,  if the incoming image changes then you lose your mask that was drawn in MaskEditor. This adds a toggle to freeze the mask in place so that it is not overwritten. Due to the custom logic that Imact Pack injects,  you will need to manually configure this node across multiple files. See the contents of impact-patches for the necessary changes.

## RestoreSizeByBounds

Don't use, currently in testing.
