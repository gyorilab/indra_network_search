// noinspection OverlyComplexBooleanExpressionJS

const isEmptyObject = function (obj) {
  for (let i in obj) {
    if (i) {
      return false;
    }
  }
  return true;
};

const evaluatesToFalse = function (thing) {
  if (Boolean(thing) === false) {
    return true
  }
  return isEmptyObject(thing)
};

const isNode = function (obj) {
  return obj.name && obj.identifier && obj.namespace;
};

const isStr = function (str, emptyOK = false) {
  const isType = typeof str === "string";
  const nonEmtpy = emptyOK || str.length > 0; // Check length if not emptyOK
  return isType && nonEmtpy;
};

const isPosNum = function (num, canBeStr = false) {
  let val;
  if (canBeStr) {
    try {
      val = Number(num);
    } catch {
      return false;
    }
  } else {
    val = num;
  }
  const isNum = typeof val === "number";
  const geqZero = val >= 0;
  return isNum && geqZero;
};

const isNodeArray = function (arr) {
  const notEmpty = arr.length > 0;
  const containsNodes = arr.every(isNode);

  return notEmpty && containsNodes;
};

const isOptionalNode = function (obj) {
  const notProvided = Boolean(obj);
  const isNodeObj = isNode(obj);
  return isNodeObj || notProvided;
};

const isSourceCount = function (obj) {
  // Empty objects are not allowed
  if (isEmptyObject(obj)) {
    return false;
  }

  // Test if key is str and value is integer/number
  for (const [key, value] of Object.entries(obj)) {
    const isSt = isStr(key);
    const isInt = Number.isInteger(value);
    const geqZero = value >= 0;
    if (!(isSt && isInt && geqZero)) {
      return false;
    }
  }
  return true;
};

const isStmtData = function (obj) {
  // Using Boolean for the simple properties that are expected to have a
  // value that does not evaluate to False
  const st = Boolean(obj.stmt_type); // String !== ''
  const ec = Boolean(obj.evidence_count); // Number > 0
  const sh = Boolean(obj.stmt_hash); //
  const sco = typeof obj.source_counts === "object";
  const scn = !isEmptyObject(obj.source_counts);
  const sc = sco && scn;
  const bl = typeof obj.belief === "number";
  const cr = typeof obj.curated === "boolean";
  const en = Boolean(obj.english);
  const ur = Boolean(obj.db_url_hash);

  return st && ec && sh && sc && bl && cr && en && ur;
};

const isStmtDataArray = function (arr) {
  const notEmpty = arr.length > 0;
  const containsStmtData = arr.every(isStmtData);
  return notEmpty && containsStmtData;
};

const isStmtTypeSupport = function (obj) {
  const stIsStr = isStr(obj.stmt_type); // str
  const stStr = Boolean(obj.stmt_type); // str
  const srcCount = isSourceCount(obj.source_counts);
  const isStmtArr =
    typeof obj.statements === "object" && isStmtDataArray(obj.statements); // List[StmtData]

  return stIsStr && stStr && srcCount && isStmtArr;
};

const isStmtTypeSupportDict = function (obj) {
  for (const [key, value] of Object.entries(obj)) {
    // Key should be string, value should be StmtTypeSupport
    const keyIsStr = isStr(key);
    const isStmtTypeSupp = isStmtTypeSupport(value);
    if (!(keyIsStr && isStmtTypeSupp)) {
      return false;
    }
  }
  return true;
};

const isEdgeData = function (obj) {
  // Check that object conforms to indra_network_search.data_models::EdgeData

  // List[Node]  # Edge supported by statements
  const isEdge = isNodeArray(obj.edge);
  // Dict[str, StmtTypeSupport]  # key by stmt_type
  const isStTpSp = isStmtTypeSupportDict(obj.statements);
  // float  # Aggregated belief
  const blf = isPosNum(obj.belief, true);
  // float  # Weight corresponding to aggregated weight
  const wgt = isPosNum(obj.weight, true);
  // Optional[int]  # Used for signed paths
  // const XX = obj.sign;
  // Union[str, float] = 'N/A'  # Set for context
  const cw = obj.context_weight;
  const ctxWgt = (isStr(cw) && cw === "N/A") || isPosNum(cw, true);
  // str  # Linkout to subj-obj level
  const url = isStr(obj.db_url_edge);
  // Dict[str, int] = {}
  const sc = isSourceCount(obj.source_counts);

  return isEdge && isStTpSp && blf && wgt && ctxWgt && url && sc;
};

const zipEqualArrays = function (arr1, arr2) {
  return arr1.map((e, i) => [e, arr2[i]]);
};

const mergeSourceCounts = function (srcObjArr) {
  // Source: https://dev.to/ramonak/javascript-how-to-merge-multiple-objects-with-sum-of-values-43fd
  // An array of source counts [{sparser: 5, isi: 1}, {sparser: 2}]
  const result = srcObjArr.reduce((srcObj, src) => {
    for (const [source, count] of Object.entries(src)) {
      if (!srcObj[source]) {
        srcObj[source] = 0;
      }
      srcObj[source] += count;
    }
    return srcObj;
  }, {});

  return result;
};

const getSourceCounts = function (stmtDataArr) {
  // Array of stmtData -> array of source counts
  let srcObjArray = [];
  for (let stmtDataObj of stmtDataArr) {
    srcObjArray.push(stmtDataObj.source_counts);
  }
  return mergeSourceCounts(srcObjArray);
};

export default {
  isEmptyObject,
  evaluatesToFalse,
  isNode,
  isStr,
  isPosNum,
  isNodeArray,
  isOptionalNode,
  isSourceCount,
  isStmtData,
  isStmtDataArray,
  isStmtTypeSupport,
  isStmtTypeSupportDict,
  isEdgeData,
  zipEqualArrays,
  mergeSourceCounts,
  getSourceCounts,
};
