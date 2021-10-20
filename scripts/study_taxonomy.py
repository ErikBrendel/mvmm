"""

RELS

0000: ignored - not a problem
1111: ignored - not a problem

0001:
Mixed concerns
Within a single module, multiple unrelated topics are handled

0010:
Independent code duplication
In independent modules, the same code exists.

0011:
Parallel Code Structures
Within a single module similar code structures have been developed separately.

0100:
Hidden Relation
Unrelated things are being modified together?

0101:
Active mixed concerns
Within a single module, multiple unrelated topics are handled and developed together

0110:
Active independent code duplication
In independent modules, the same code is being developed and maintained in parallel.

0111:
Active parallel Code Structures
Within a single module similar code structures have been developed together.

1000: (weird)

there are not really any results here

1001: (weird)
Mixed concerns on same data
within a single module, vastly different tasks are allowed on the same data structures (?)

1010:
Code Clone?
separate modules that are doing similar things

1011:
Close Code Clones
methods within a module that are doing similar things

1100:
Hidden cross-cutting concern
Separate modules are developed together because they need each other.

1101:
Inconsistent language
modules that are linked, but contain largely different vocabulary

1110:
Cross-cutting concerns?
Strongly related methods from different modules.



=======================

compressed

RELS

0000 - ignored
1111 - ignored
100* - weird / ignored, since not a problem

101* - direct code clones
11*0 - cross cutting concerns
0*10 - independent code duplication
0*11 - parallel structures within a module
0*01 - mixed concerns (maybe not a problem?)
0100 - Hidden Relation
1101 - Inconsistent language




















"""