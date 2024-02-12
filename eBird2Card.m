
% A card is defined by three elements: pentad_code, user_id and date of
% the first day of the 5 days.
% From a card id {pentad}_{observer}_{date}, it is possible to find all
% checklists that belongs to it.
% The aim here is to build a list of valid card which will then be used to
% find the checklist_id which belong to this card and then finally compute
% the card info from the list of checklists.

% * Pentad: we need to assign for each checklist its pentand and check that
% the distance travel is within the boundary of the pentad
% * User_id is quite straightward to build.
% * date: much more challenging. see below for details.
addpath("functions/")

tic
%% Set up the Import Options and import the data
cntr = "ZA";
ebd0 = readEBD("data/eBird/ebd_"+cntr+"_relAug-2022/ebd_"+cntr+"_relAug-2022.txt");
toc
% sort by date: possibly needed for sequence
ebd0 = sortrows(ebd0,"OBSERVATIONDATE");

%% Keep only species category
% writetable(unique(ebd0(:,["COMMONNAME", "SCIENTIFICNAME", "CATEGORY"]),"rows"),"species_list_ebird.csv")

% remove domestic chicken
ebd0 = ebd0(ebd0.SCIENTIFICNAME~="Gallus gallus (Domestic type)",:);

% Keep some spuh which can be match to an ADU
spuh_keep = readtable("data/spuh_keep.csv","TextType","string");
% Remove slash and spuh not recongnized
ebd0 = ebd0((ebd0.CATEGORY~="spuh" & ebd0.CATEGORY~="slash") | ismember(ebd0.SCIENTIFICNAME,spuh_keep.Clements__scientific_name),:);

%% Build checklist level
ebd = groupsummary(ebd0,["SAMPLINGEVENTIDENTIFIER","LATITUDE","LONGITUDE","OBSERVATIONDATE", "TIMEOBSERVATIONSSTARTED","PROTOCOLTYPE","DURATIONMINUTES","EFFORTDISTANCEKM","ALLSPECIESREPORTED","OBSERVERID"]);
ebd = sortrows(ebd,"OBSERVATIONDATE");

%% Filter protocol
ebd.KEEP_PROTOCOL = ismember(ebd.PROTOCOLTYPE, categorical(["Historical", "Incidental", "Stationary", "Traveling"]));
% mean(ebd.KEEP_PROTOCOL) 99%

%% Pentad

% Assign to pentad and check if distance remains inside
ebd.PENTAD = latlon2pentad(ebd.LATITUDE, ebd.LONGITUDE);

%Search center of pentad
[lat,lon] = pentad2latlng(ebd.PENTAD);
% ebd.distcenter = deg2km(distance(ebd.LATITUDE, ebd.LONGITUDE, lat, lon));

% Filter distance
dist = (5/60/2)*1.2;%.2; % allow for a 20% overlap.
ebd.KEEP_PENTAD = ~(km2deg(ebd.EFFORTDISTANCEKM)+max(abs(lat-ebd.LATITUDE), abs(lon-ebd.LONGITUDE))>dist);
% mean(ebd.KEEP_PENTAD) % 66% -> 73% for 1.2 overlap

% Also filter historical checklist which have no distance
ebd.KEEP_PENTAD(ebd.PROTOCOLTYPE == "Historical" & isnan(ebd.EFFORTDISTANCEKM)) = false;
% mean(ebd.KEEP_PENTAD) 88%

% mean(ebd.KEEP_PENTAD) 53% 60%

%% Find the ID of the valid card_id
% a card ID is defined by PENTAD + OBSERVERID + OBSERVATIONDATE
% We need to find the valid a card was valid sum(duration)>2hours over the next
% rolling 5 days. So we need to convert the checklists into card and then
% delete all the checklist_card which are not valid or are merged into a
% single card.

% filter for valid pentad and format in a smaller table
% Remove all checklists which don't have duration as they will not
% contribute to the validaty of a card. Note that we will still use them
% later once we know the valid card.
id = ebd.KEEP_PENTAD & ebd.KEEP_PROTOCOL & ebd.DURATIONMINUTES>0 & ebd.ALLSPECIESREPORTED;
% mean(ebd.KEEP_PROTOCOL) %55%;
% sum(id) 23%
check = table(ebd.PENTAD(id), ebd.OBSERVERID(id), datenum(ebd.OBSERVATIONDATE(id)), ebd.DURATIONMINUTES(id)/60,...
    variableName=["pentad", "observer", "date", "duration"]);

% Combine checklists made by the same observer, pentand and day.
checkday = groupsummary(check,["pentad","observer","date"],"sum","duration");
% height(checkday) 19K

% Sort the checklist by id and date to be able to do the rolling check on a continuis windows
checkday = sortrows(checkday,"date");

%
checkday.pentad_observer = checkday.pentad + "_" + checkday.observer;
checkday.pentad_observer_date = checkday.pentad + "_" + extractAfter(checkday.observer,4) + "_" + string(datetime(checkday.date, "ConvertFrom","datenum"),"yyyyMMdd");

% extract the unique pentand_observer combo
unique_pentad_observer = unique(checkday.pentad_observer);

checkday.card(:) = "";

% sortrows(groupsummary(checkday,"pentad_observer"),"GroupCount","descend")
% i = find("0325_3835_obsr556698"==unique_pentad_observer)

% loop through each pentad_observer
for i=1:numel(unique_pentad_observer)
    % find all the checklist from this pentad_obs
    pentad_observer = find(checkday.pentad_observer==unique_pentad_observer(i));

    % Build a logical matrix of all pentad_obs and if they are within the 5
    % days limits
    di = abs(checkday.date(pentad_observer)-checkday.date(pentad_observer)')<5;

    u=1;
    while u <= numel(pentad_observer)
        % finding the number of neighbor cheklists which are within the 5 days
        % limits, starting at the current checklist u. Should be at least
        nb_neighbor = sum(di(u,u:end));
        % use the index of these neighbors
        neigh =  u+(0:(nb_neighbor-1));
        % Computing the duration of all the checklists within the 5 day
        % periods
        dur = checkday.sum_duration(pentad_observer(neigh));
        if sum(dur)>=2
            % Valid/full card
            % Assign the index of first checklist of the card to all the
            % checklist
            checkday.card(pentad_observer(neigh)) = checkday.pentad_observer_date(pentad_observer(u));
        end
        % start the next search on the next checklist or the checklist in
        % the next 5 days.
        u = u + nb_neighbor;
    end
end


card = checkday(checkday.card == checkday.pentad_observer_date,["pentad", "observer", "date", "card"]);
% card.date = datetime(card.date, "ConvertFrom","datenum");
% height(card) 4269
%% Create Card

ebd.OBSERVATIONDATE_num = datenum(ebd.OBSERVATIONDATE);
ebd.card(:) = "";
ebd.OBSERVATIONDATETIME = datetime(string(ebd.OBSERVATIONDATE, "yyyy-MM-dd")  + " " + string(ebd.TIMEOBSERVATIONSSTARTED, "HH:mm:ss") );

d = cell(height(card),1);
for i_card = 1:height(card)

    id = ebd.KEEP_PENTAD & ebd.PENTAD == card.pentad(i_card) & ebd.OBSERVERID == card.observer(i_card) & ebd.OBSERVATIONDATE_num >= card.date(i_card) & ebd.OBSERVATIONDATE_num < card.date(i_card)+5;
    assert(all(ebd.card(id)==""))
    ebd.card(id) = card.card(i_card);

    % Import format
    d{i_card}.Protocol = "F";
    d{i_card}.ObserverEmail = "kenyabirdmap@naturekenya.org";
    d{i_card}.CardNo = card.card(i_card);
    d{i_card}.StartDate = string(min(ebd.OBSERVATIONDATE(id)), "yyyy-MM-dd");
    d{i_card}.EndDate = string(max(ebd.OBSERVATIONDATE(id)), "yyyy-MM-dd");
    d{i_card}.StartTime = string(min(ebd.OBSERVATIONDATETIME(id)), "HH:mm");
    d{i_card}.Pentad = card.pentad(i_card);
    d{i_card}.ObserverNo = "22829";
    d{i_card}.TotalHours = nansum(ebd.DURATIONMINUTES(id))/60;
    d{i_card}.Hour1 = "";
    d{i_card}.Hour2 = "";
    d{i_card}.Hour3 = "";
    d{i_card}.Hour4 = "";
    d{i_card}.Hour5 = "";
    d{i_card}.Hour6 = "";
    d{i_card}.Hour7 = "";
    d{i_card}.Hour8 = "";
    d{i_card}.Hour9 = "";
    d{i_card}.Hour10 = "";
    d{i_card}.TotalSpp = 0;
    d{i_card}.InclNight = "0";
    d{i_card}.AllHabitats = "0";
    d{i_card}.Checklists = ebd.SAMPLINGEVENTIDENTIFIER(id);
    d{i_card}.TotalDistance = nansum(ebd.EFFORTDISTANCEKM(id));
    d{i_card}.ObserverNoEbird = card.observer(i_card);
end

% sum(cellfun(@(x) numel(x.Checklists), d)) 13K 33K(ZA)

%% Get species level information

% Filter the full dataset to get only the checklist  valid...
tmp = cellfun(@(x) x.Checklists, d, 'UniformOutput', false);
all_checklists = vertcat(tmp{:});
ebd0f = ebd0(ismember(ebd0.SAMPLINGEVENTIDENTIFIER, all_checklists),["SAMPLINGEVENTIDENTIFIER", "SCIENTIFICNAME"]);

% slow
% for i_card = 1:height(card)
%     id2 = ismember(ebd0f.SAMPLINGEVENTIDENTIFIER, d{i_card}.Checklists);
%     d{i_card}.Species = unique(ebd0f.SCIENTIFICNAME(id2));
%     d{i_card}.TotalSpp = numel(d{i_card}.Species);
% end

% Add ADU number
species_match = readtable("data/species_match.csv","TextType","string");
species_match = species_match( ~isnan(species_match.ADU) & ~ismissing(species_match.Clements__scientific_name),["ADU","Clements__scientific_name"]);

% Add missing species
species_match = [species_match; spuh_keep;
    table([10958, 941, 10046 456]',...
    ["Emberiza goslingi", "Psittacula krameri" "Zosterops eurycricotus" "Mirafra cheniana"]',...
    VariableNames=["ADU", "Clements__scientific_name"])];

% Check that all entry are matching
unique(ebd0f.SCIENTIFICNAME(~ismember(ebd0f.SCIENTIFICNAME, species_match.Clements__scientific_name)))

% Add ADU number
ebd0f = join(ebd0f, species_match, LeftKeys="SCIENTIFICNAME", RightKeys="Clements__scientific_name");
% any(isnan(ebd0f2.ADU))

% Get card_id for each observation
tmp2 = cellfun(@(x) numel(x.Checklists), d);
tmp3 = repelem((1:numel(tmp2))',tmp2);
[~, id] = ismember(ebd0f.SAMPLINGEVENTIDENTIFIER, all_checklists);
ebd0f.card_id = tmp3(id);

% Extract the species list per card as a cell for vectorized computation
sp_list = splitapply(@(x) {unique(x, "stable")}, ebd0f.ADU, ebd0f.card_id);


% Sequence of checklist
% Find the sequence of the checklist
[~, id] = ismember(ebd0f.SAMPLINGEVENTIDENTIFIER, unique(ebd0f.SAMPLINGEVENTIDENTIFIER, 'stable'));
ebd0f.checklist_seq = id;
% Find the first checklist for each species of each card
ebd0fG = groupsummary(ebd0f, ["card_id", "ADU"], "min", "checklist_seq");

sp_list_seq = splitapply(@(x) {x}, ebd0fG.min_checklist_seq, ebd0fG.card_id);

% Add to card
for i_card = 1:height(card)
    d{i_card}.records = cell(numel(sp_list{i_card}),1);

    [C,ia,ic] = unique(sp_list_seq{i_card});

    for i_sp = 1:numel(sp_list{i_card})
        d{i_card}.records{i_sp}.Sequence = ic(i_sp);
        d{i_card}.records{i_sp}.Latitude = "";
        d{i_card}.records{i_sp}.Longitude = "";
        d{i_card}.records{i_sp}.Altitude = "";
        d{i_card}.records{i_sp}.CardNo = d{i_card}.CardNo;
        d{i_card}.records{i_sp}.Spp = sp_list{i_card}(i_sp);
        d{i_card}.records{i_sp}.Accuracy = "";
        d{i_card}.records{i_sp}.SightingTime = "";
    end
    d{i_card}.TotalSpp = numel(sp_list{i_card});
end

%% Minor check and filter
% d{cellfun(@(x) x.TotalSpp<3, d)}



%% Export/Save

fname = "export/"+cntr+"_data";

% json
fid = fopen(fname + ".json",'w');
fprintf(fid,'%s',jsonencode(d));
fclose(fid);

%% Export to csv
% Convert the structure array to a table
% Convert the structure array to a table
T = struct2table(vertcat(d{:}));
T = T(tmp4,:);
T.Spp = ebd0f.ADU;
T.Sequence(:) = 0;
T.ObserverName = T.ObserverNoEbird;

sp_kbm = readtable("data/kbm/sp_kbm.xlsx", TextType="string");  

% T2 = join(T, sp_kbm, LeftKeys = "Spp", RightKeys = "Ref");
T.Common_group(:) = "";
T.Common_species(:) = "";
T.Genus(:) = "";
T.Species(:) = "";

% id = ismember(T.Spp, sp_kbm.Ref);

Tout = T(:, ["CardNo" "StartDate" "EndDate" "StartTime" "Pentad" "ObserverNo" "ObserverName" "TotalHours" ...
    "Hour1" "Hour2" "Hour3" "Hour4" "Hour5" "Hour6" "Hour7" "Hour8" "Hour9" "Hour10" ...
    "TotalSpp" "InclNight" "AllHabitats" "Spp" "Common_group" "Common_species" "Genus" "Species" "Sequence" "TotalDistance" "Checklists"]);

writetable(Tout, "export/eBird_fullcard_ "+string(datetime("now", format ="yyyyMMdd"))+".csv")



%%

observer = groupsummary(table(cellfun(@(x) x.ObserverNoEbird, d)), "Var1");
observer = sortrows(observer,"GroupCount");

figure; histogram(cellfun(@(x) x.TotalHours, d)); xlabel("TotalHours")
figure; histogram(cellfun(@(x) numel(x.Checklists), d)); xlabel("Checklists Number")
figure; histogram(cellfun(@(x) x.TotalSpp, d)); xlabel("TotalSpp")
figure; histogram(groupcounts()); xlabel("ObserverNo")
figure; histogram(groupcounts(cellfun(@(x) x.Pentad, d))); xlabel("Pentad")

[~,id]=sort(cellfun(@(x) numel(x.Checklists), d),"descend");
d{id(end)}.Checklists

[~,id]=sort(cellfun(@(x) x.TotalSpp, d));
d{id(1)}.Checklists




ebd0f(ebd0f.SAMPLINGEVENTIDENTIFIER=="S46450134",:)

find(card.card=="0050_3615_1055177_19870104")