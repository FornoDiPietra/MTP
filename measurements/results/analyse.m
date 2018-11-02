%fileName = 'patch_98_max_2M.txt';
fileName = uigetfile('.txt');
timeElapsed = 1;
NumberOfPacketsSent = 20000;

% read in the file with the received packets
fileID = fopen(fileName,'r');
formatSpec = '%d';
receivedPackets = fscanf(fileID,formatSpec);
fclose(fileID);

numOfRcvPackets = numel(receivedPackets);

% make a vector with the missing packets
missingPackets = [];
missingPacketCounter = 0;
timeAxis = [];

for i=2:numOfRcvPackets
    
    step = receivedPackets(i) - receivedPackets(i-1);
    if (step > 1)
       missingPacketCounter=missingPacketCounter+1;
       missingPackets(missingPacketCounter) = step-1;
       timeAxis(missingPacketCounter) = receivedPackets(i-1)+1;
        
    end
    
end

timeAxis = timeAxis .* (timeElapsed / NumberOfPacketsSent);

stem(timeAxis,missingPackets,'Marker','none');