function ebd = readEBD(file)

% Set up the Import Options and import the data
opts = delimitedTextImportOptions("NumVariables", 49);

% Specify range and delimiter
opts.DataLines = [1, Inf];
opts.Delimiter = "\t";

% Specify column names and types
opts.VariableNames = ["GLOBALUNIQUEIDENTIFIER", "LASTEDITEDDATE", "TAXONOMICORDER", "CATEGORY", "TAXONCONCEPTID", "COMMONNAME", "SCIENTIFICNAME", "SUBSPECIESCOMMONNAME", "SUBSPECIESSCIENTIFICNAME", "EXOTICCODE", "OBSERVATIONCOUNT", "BREEDINGCODE", "BREEDINGCATEGORY", "BEHAVIORCODE", "AGESEX",    "COUNTRY",     "COUNTRYCODE", "STATE",       "STATECODE", "COUNTY",        "COUNTYCODE", "IBACODE", "BCRCODE",         "USFWSCODE",    "ATLASBLOCK", "LOCALITY", "LOCALITYID", "LOCALITYTYPE", "LATITUDE", "LONGITUDE", "OBSERVATIONDATE", "TIMEOBSERVATIONSSTARTED", "OBSERVERID", "SAMPLINGEVENTIDENTIFIER", "PROTOCOLTYPE", "PROTOCOLCODE", "PROJECTCODE", "DURATIONMINUTES", "EFFORTDISTANCEKM", "EFFORTAREAHA", "NUMBEROBSERVERS", "ALLSPECIESREPORTED", "GROUPIDENTIFIER", "HASMEDIA", "APPROVED", "REVIEWED", "REASON", "TRIPCOMMENTS", "SPECIESCOMMENTS"];
opts.VariableTypes = ["string",                 "datetime",         "int64",       "categorical", "string",         "string",   "string",            "string",           "string",                    "categorical","int64",            "categorical",  "categorical",      "categorical","categorical", "categorical", "categorical", "categorical", "categorical", "categorical", "categorical", "categorical", "categorical", "categorical", "categorical","string", "categorical", "categorical",    "double",   "double",       "datetime",     "datetime",                 "string",       "string",               "categorical", "categorical", "categorical", "int64",          "double",            "double",       "int64",           "int8",              "string",              "int8",    "int8",       "int8",     "string", "string",      "string",        ];

% Specify variable properties
%opts = setvaropts(opts, ["GLOBALUNIQUEIDENTIFIER", "SUBSPECIESCOMMONNAME", "SUBSPECIESSCIENTIFICNAME", "EXOTICCODE", "BREEDINGCODE", "BREEDINGCATEGORY", "BEHAVIORCODE", "AGESEX", "COUNTY", "COUNTYCODE", "IBACODE", "BCRCODE", "USFWSCODE", "ATLASBLOCK", "SAMPLINGEVENTIDENTIFIER", "DURATIONMINUTES", "EFFORTDISTANCEKM", "EFFORTAREAHA", "GROUPIDENTIFIER", "REASON", "TRIPCOMMENTS", "SPECIESCOMMENTS", "VarName50"], "WhitespaceRule", "preserve");
%opts = setvaropts(opts, ["GLOBALUNIQUEIDENTIFIER", "CATEGORY", "TAXONCONCEPTID", "COMMONNAME", "SCIENTIFICNAME", "SUBSPECIESCOMMONNAME", "SUBSPECIESSCIENTIFICNAME", "EXOTICCODE", "BREEDINGCODE", "BREEDINGCATEGORY", "BEHAVIORCODE", "AGESEX", "COUNTRY", "COUNTRYCODE", "STATE", "STATECODE", "COUNTY", "COUNTYCODE", "IBACODE", "BCRCODE", "USFWSCODE", "ATLASBLOCK", "LOCALITYID", "LOCALITYTYPE", "OBSERVERID", "SAMPLINGEVENTIDENTIFIER", "PROTOCOLTYPE", "PROTOCOLCODE", "PROJECTCODE", "DURATIONMINUTES", "EFFORTDISTANCEKM", "EFFORTAREAHA", "GROUPIDENTIFIER", "REASON", "TRIPCOMMENTS", "SPECIESCOMMENTS", "VarName50"], "EmptyFieldRule", "auto");
opts = setvaropts(opts, "LASTEDITEDDATE", "InputFormat", "yyyy-MM-dd HH:mm:ss");
opts = setvaropts(opts, "OBSERVATIONDATE", "InputFormat", "yyyy-MM-dd");
opts = setvaropts(opts, "TIMEOBSERVATIONSSTARTED", "InputFormat", "HH:mm:ss");

% Read Data
ebd = readtable(file, opts);

% Post processing https://www.mathworks.com/matlabcentral/answers/895897-readtable-not-reading-logical-values-as-expected
ebd.ALLSPECIESREPORTED = logical(ebd.ALLSPECIESREPORTED);
ebd.HASMEDIA = logical(ebd.HASMEDIA);
ebd.APPROVED = logical(ebd.APPROVED);
ebd.REVIEWED = logical(ebd.REVIEWED);

% Issue with the reading probably... 
ebd(ebd.SAMPLINGEVENTIDENTIFIER=="SAMPLING EVENT IDENTIFIER",:)=[];

end