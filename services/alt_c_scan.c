#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <bluetooth/bluetooth.h>
#include <bluetooth/hci.h>
#include <bluetooth/hci_lib.h>

void process_data(uint8_t *data, int len) {
    int16_t battery = (data[len - 10] << 8) | data[len - 9];
    int16_t x = (data[len - 6] << 8) | data[len - 5];
    int16_t y = (data[len - 4] << 8) | data[len - 3];
    int16_t z = (data[len - 2] << 8) | data[len - 1];

    printf("Accelerometer X: %d\n", x);
    printf("Accelerometer Y: %d\n", y);
    printf("Accelerometer Z: %d\n", z);
    printf("Battery Level  : %d\n", battery);
}

void device_found(le_advertising_info *info) {
    char addr[19] = { 0 };
    ba2str(&info->bdaddr, addr);

    if (strstr(addr, "DD:34")) {
        printf("Device Address: %s\n", addr);
        printf("RSSI          : %d dBm\n", info->data[info->length]);
        printf("-----------------------------------------------\n");

        // Assuming Eddystone data is in the service data
        uint8_t *eddystone_data = info->data + 9; // Adjust offset as needed
        process_data(eddystone_data, info->length - 9);
        printf("-----------------------------------------------\n");
    }
}

int main() {
    int device_id = hci_get_route(NULL);
    int sock = hci_open_dev(device_id);
    if (device_id < 0 || sock < 0) {
        perror("Opening socket");
        exit(1);
    }

    struct hci_filter nf;
    hci_filter_clear(&nf);
    hci_filter_set_ptype(HCI_EVENT_PKT, &nf);
    hci_filter_set_event(EVT_LE_META_EVENT, &nf);
    if (setsockopt(sock, SOL_HCI, HCI_FILTER, &nf, sizeof(nf)) < 0) {
        perror("Setting socket options");
        close(sock);
        exit(1);
    }

    uint8_t own_type = LE_PUBLIC_ADDRESS;
    uint8_t scan_type = 0x01; // Active scanning
    uint16_t interval = htobs(0x0010);
    uint16_t window = htobs(0x0010);
    uint8_t filter_policy = 0x00;
    uint8_t filter_dup = 0x01;

    if (hci_le_set_scan_parameters(sock, scan_type, interval, window, own_type, filter_policy, 10000) < 0) {
        perror("Set scan parameters");
        close(sock);
        exit(1);
    }

    if (hci_le_set_scan_enable(sock, 0x01, filter_dup, 10000) < 0) {
        perror("Enable scan");
        close(sock);
        exit(1);
    }

    while (1) {
        uint8_t buf[HCI_MAX_EVENT_SIZE];
        int len = read(sock, buf, sizeof(buf));
        if (len < 0) {
            perror("Reading socket");
            break;
        }

        evt_le_meta_event *meta = (evt_le_meta_event *)(buf + (1 + HCI_EVENT_HDR_SIZE));
        if (meta->subevent != EVT_LE_ADVERTISING_REPORT) continue;

        le_advertising_info *info = (le_advertising_info *)(meta->data + 1);
        device_found(info);
    }

    hci_close_dev(sock);
    return 0;
}
