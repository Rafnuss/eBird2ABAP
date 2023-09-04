
% Download the data for all species in geojson

sp_kbm = readtable("data/kbm/sp_kbm.xlsx", 'TextType', 'string');


opts = weboptions("Timeout",60);
for i_sp=501:height(sp_kbm)
    filename = "data/kbm/csv/"+sp_kbm.Ref(i_sp)+".csv";
    if ~isnan(sp_kbm.Ref(i_sp)) % && ~exist(filename,'file')
        sp_kbm.Ref(i_sp)
        websave(filename,"https://api.birdmap.africa/sabap2/v2/R/2007-07-01/2025-01-01/country/kenya/data/species/"+sp_kbm.Ref(i_sp)+"?format=CSV",opts)
        pause(5)
    end
end


% Define the directory where your files are
dir_path = 'data/kbm/csv/';

% Get list of all csv files in the directory
file_list = dir(fullfile(dir_path, '*.csv')); 
num_files = length(file_list);

% Preallocate cell array
data_cell = cell(num_files, 1);

opts = delimitedTextImportOptions('VariableTypes', {'string', 'datetime', 'datetime', 'duration', 'string', 'double', 'string', 'double', 'double', ...
                 'double', 'double', 'double', 'double', 'double', 'double', 'double', 'double', 'double', ...
                 'double', 'double', 'double', 'double', 'string', 'string', 'string', 'string', 'double'});

opts = detectImportOptions(fullfile(dir_path, file_list(1).name), TextType="string");

% Loop through each file
for k = 1:num_files
    % Read the csv file into a table and store it in the cell array
    data_cell{k} = readtable(fullfile(dir_path, file_list(k).name), opts);
end

% Vertically concatenate all tables in the cell array
merged_data = vertcat(data_cell{cellfun(@height,data_cell)>1});

% Write the merged data to a new csv file
writetable(merged_data, fullfile(dir_path, 'merged.csv'));
