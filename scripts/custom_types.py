
from typing import *

PatternType = List[Union[float, int, None, str]]
PatternsType = List[PatternType]
AnalysisResultType = Tuple[Tuple[float, ...], Tuple[str, str, Tuple[float, ...]]]
PairAnalysisResultsType = List[List[AnalysisResultType]]
