function s = latlon2pentad(lat, lng)
    letter = strings(size(lat,1),size(lat,2));
    letter(lat <= 0 & lng > 0) = '_';
    letter(lat < 0 & lng < 0) = 'a';
    letter(lat > 0 & lng < 0) = 'b';
    letter(lat > 0 & lng > 0) = 'c';

	lat2 = abs(lat + 0.0001);
    lat2(lat>0) = lat2(lat>0) + (5/60);
	lng2 = abs(lng + 0.0001);
	latDeg = floor(lat2);
	lngDeg = floor(lng2);
	latSec = floor((lat2 - latDeg) * 60 / 5) * 5;
	lngSec = floor((lng2 - lngDeg) * 60 / 5) * 5;

    latstr = strings(size(lat,1),size(lat,2));
    lngstr = latstr;
    for i1=1:size(lat,1)
        for i2=1:size(lat,2)
            latstr(i1,i2) = [sprintf('%02d',latDeg(i1,i2))  sprintf('%02d',latSec(i1,i2))];
            lngstr(i1,i2) = [sprintf('%02d',lngDeg(i1,i2))  sprintf('%02d',lngSec(i1,i2))];
        end
    end

	s = latstr + letter + lngstr;
end
