#define BLOCKSIZE 29
#define PACKET_STACK_SIZE 65000
#define BURST_SIZE 256

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

struct Packet {
	char seqNumber[2];
	char data[29];
	char valid;
	char confirmed;
};

struct Frame {
	struct Packet *packet;
	char burstId;
	char ack;
	char valid;
};

void initStack(struct Packet *stack, int len) {
	for (int i=0; i<len; i++) {
		stack[i].valid = 0;	
		stack[i].confirmed = 0;
	}
}

int addPadding(char *buf, char pad, int start, int len) {
	for (int i=start; i<len; i++) {
		buf[i] = pad;
	}
	return len-start;	
}

void createMagicPacket(struct Packet *packet, int maxSeqNumber, int padding) {
	packet->valid = 1;
	for (int i=0; i<BLOCKSIZE; i++) {
		packet->data[i] = 0;
	}
	packet->data[1] = maxSeqNumber & 0xff;
	packet->data[0] = maxSeqNumber>>8 & 0xff;
	packet->data[3] = padding & 0xff;
	packet->data[2] = padding>>8 & 0xff;
}

void loadStackFromFile(char *fileName, struct Packet *stack) {
	char buf[BLOCKSIZE];
	FILE *file;
	size_t nread;
	int j=1;
	int padding=0;

	file = fopen(fileName, "r");
	if (file) {
	    while ((nread = fread(buf, 1, sizeof buf, file)) > 0 && j < PACKET_STACK_SIZE) {
	    	padding = addPadding(buf, 0, nread, BLOCKSIZE);

	    	//----set the sequence number-----
	    	stack[j].seqNumber[1] = j & 0xff;
	    	stack[j].seqNumber[0] = j>>8 & 0xff;

	    	//----copy to the packet stack----
	    	for (int i=0; i<BLOCKSIZE; i++) {
	    		stack[j].data[i] = buf[i];
	    	}

	    	//----validate the packet---------
	    	stack[j].valid = 1;
	    	j++;
	    }
	    fclose(file);
	    createMagicPacket(stack, j-1, padding);
	    printf("sending %d packets (max seq num %d)\n",j,j-1);
	}	
}

void printStack(struct Packet *stack, int from, int to) {
	int seqNumber=0;

	for (int i=from; i<to; i++) {
		if (stack[i].valid != 0) {
			seqNumber = stack[i].seqNumber[0]<<8 | stack[i].seqNumber[1];

			printf("%5d | ",seqNumber);
			for (int j=0; j<29; j++) {
				printf("%3d ",stack[i].data[j]);
			}

			if (stack[i].confirmed != 0)
				printf(" | x\n");
			else
				printf(" |  \n");
		}
	}	
}

int getBurst(struct Packet *stack, struct Frame *burst, int startAt) {
	int j = 0;
	int i = startAt;
	int firstFound = 0;	//remember at which position we found the first packet

	while (j < BURST_SIZE) {
		if (stack[i].confirmed == 0 && stack[i].valid != 0) {
			if (firstFound == 0)
				firstFound = j;

			burst[j].packet = stack+i;
			burst[j].burstId = j;
			burst[j].valid = 1;
			burst[j].ack = 0;
			j++;
		}
		i++;
		if (i >= PACKET_STACK_SIZE)
			i=startAt;
	}

	return firstFound;
}

void printBurst(struct Frame *burst) {
	int seqNum = 0;

	for (int i=0; i<BURST_SIZE; i++) {
		if (burst[i].valid != 0) {

			printf("%3d | ", i);

			printf("%3d ", burst[i].packet->seqNumber[0]);
			printf("%3d ", burst[i].packet->seqNumber[1]);

			for (int j=0; j<29; j++) {
				printf("%3d ",burst[i].packet->data[j]);
			}

			if (burst[i].ack == 0)
				printf("|\n");
			else
				printf("| x\n");

		}
	}
}

void ackBurst(struct Frame *burst, char *ack) {
	for (int byteIndex=0; byteIndex<(BURST_SIZE/8)+1; byteIndex++) {

		for (int bitIndex=0; bitIndex<8; bitIndex++) {

			if ( (ack[byteIndex] & 0x01<<bitIndex) == 0) {
				//NOACK
			} else {
				//ACK
				burst[(8*byteIndex)+bitIndex].ack = 1;
			}
		}

	}
}

void confirmStackFromBurst(struct Frame *burst, struct Packet *stack) {
	// check all the packets in the stack that were confirmed
	// in this burst
	for (int i=0; i<BURST_SIZE; i++) {
		if (burst[i].ack != 0 && burst[i].valid != 0) {
			burst[i].packet->confirmed = 1;
		}
	}

}

int isStackAllConfirmed(struct Packet *stack) {
	// check if there is a valid packet in the stack
	// that is not confirmed yet
	for (int i=0; i<PACKET_STACK_SIZE; i++) {
		if (stack[i].valid != 0 && stack[i].confirmed == 0)
			return 0;
	}
	return 1;
}

int initBurst(struct Frame *burst) {
	for (int i=0; i<BURST_SIZE; i++) {
		burst[i].valid = 0;
		burst[i].ack = 0;
	}
}

int addRawFrameToBurst(struct Frame *burst, struct Packet *stack, char *rawFrame) {
	int burstId, seqNumber;
	struct Packet *packet;

	burstId = rawFrame[0];
	seqNumber = rawFrame[1]<<8 | rawFrame[2];

	packet = &stack[seqNumber];

	burst[burstId].burstId = burstId;
	burst[burstId].valid = 1;
	burst[burstId].packet = packet;

	if (packet->valid == 0) {
		packet->seqNumber[0] = rawFrame[1];
		packet->seqNumber[1] = rawFrame[2];
		packet->valid = 1;

		for (int i=0; i<BLOCKSIZE; i++) {
			packet->data[i] = rawFrame[3+i];
		}
		return 1;
	}
	return 0;
	
}

void rawDataFromFrame(char *buf, struct Frame *frame) {
	buf[0] = frame->burstId;
	buf[1] = frame->packet->seqNumber[0];
	buf[2] = frame->packet->seqNumber[1];

	for (int i=0; i<BLOCKSIZE; i++) {
		buf[i+3] = frame->packet->data[i];
	}
}

int complete(struct Packet *stack, int nRcv) {
	int maxSeqNumber;

	if (stack[0].valid != 0) {
		maxSeqNumber = stack[0].data[0]<<8 | stack[0].data[1];
		if (nRcv >= maxSeqNumber)
			return 1;
	}
	return 0;
}

void setBit(char *buf, int pos) {
	int bytePos = (pos/8);
	int bitPos  = pos % 8;
	buf[bytePos] = buf[bytePos] | (0x01<<bitPos);
}
void clearBit(char *buf, int pos) {
	int bytePos = (pos/8);
	int bitPos  = pos % 8;
	buf[bytePos] = buf[bytePos] & ~(0x01<<bitPos);	
}

void generateAckFrame(char *buf, struct Frame *burst) {
	for (int i=0; i<BURST_SIZE; i++) {
		if (burst[i].valid)
			setBit(buf, i);
		else
			clearBit(buf, i);
	}
}
int main()
{
	int startSearch = 0;
	int packetRcv = 0;

	char ack[32];

	struct Packet stack[PACKET_STACK_SIZE];
	struct Frame burst[BURST_SIZE];

	struct Packet rxStack[PACKET_STACK_SIZE];
	struct Frame rxBurst[BURST_SIZE];

	initStack(stack,PACKET_STACK_SIZE);
	loadStackFromFile("test.txt", stack);

	initStack(rxStack,PACKET_STACK_SIZE);
	initBurst(rxBurst);

	srand(time(NULL));

	int burstNum = 0;

	while (1) {

		//printf("--Tx Packet Stack ------\n");
		//printStack(stack);
		initBurst(rxBurst);

		if (burstNum % 10 == 0) {
			printf("burst: %d\n",burstNum);
			printf("packetRcv: %d\n", packetRcv);
			printf("startSearch: %d\n", startSearch);
		}
		burstNum++;

		startSearch = getBurst(stack, burst, startSearch);

		//printf("--Tx Burst--------------\n");
		//printBurst(burst);

		char rawDataBuffer[32];
		// Transmit the whole burst
		for (int i=0; i<BURST_SIZE; i++) {
			if (burst[i].valid != 0) {
				if ( (rand() % 100) >= 80) {
					rawDataFromFrame(rawDataBuffer, &burst[i]);
					if (addRawFrameToBurst(rxBurst,rxStack,rawDataBuffer))
						packetRcv++;
				}
			}
		}

		//printf("--Rx Burst--------------\n");
		//printBurst(rxBurst);

		//printf("--Rx Stack--------------\n");
		//printStack(rxStack);

		//printf("sending ACK... \n");
		if ( (rand() % 100) >= 20) {
			generateAckFrame(ack, rxBurst);
			ackBurst(burst,ack);
		}
		//printf("--Tx Burst after Ack------\n");
		//printBurst(burst);

		confirmStackFromBurst(burst,stack);

		//printf("--Tx Stack after ACK------\n");
		//printStack(stack,0,20);



		if (complete(stack,packetRcv) == 0)
		{}	//printf("not confirmed\n");
		else {
			printf("confirmed\n");
			break;
		}

		//getchar(); 
		//printf("###############################################\n######################################\n");

	}

   	return 0;
}